from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from dotenv import load_dotenv
import os
import logging
from functools import wraps
from app.zabbix_api import ZabbixAPI, debug_print

load_dotenv()

app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv('DEBUG_ENABLED', 'false').lower() in ['true', '1', 'yes', 'on'] else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===============================
# HELPER FUNCTIONS
# ===============================

def validate_tag_request(data):
    """Validate tag request data. Returns (tag_name, tag_value, error_response)"""
    if not data:
        return None, None, jsonify({'success': False, 'message': 'Invalid request - JSON required'})

    tag_name = data.get('tag')
    tag_value = data.get('value', '')

    if not tag_name or not isinstance(tag_name, str) or tag_name.strip() == '':
        return None, None, jsonify({'success': False, 'message': 'Tag name is required'})

    if len(tag_name) > 255 or (tag_value and len(tag_value) > 255):
        return None, None, jsonify({'success': False, 'message': 'Tag name or value too long (max 255 characters)'})

    return tag_name, tag_value, None

def get_authenticated_zabbix():
    """Get authenticated ZabbixAPI instance. Returns (zabbix, error_response)"""
    zabbix = ZabbixAPI()
    if not zabbix.authenticate():
        return None, jsonify({'success': False, 'message': 'Authorization error'})
    return zabbix, None

def parse_ids_list(ids_raw, entity_name='items'):
    """Parse list of IDs (can be comma-separated strings). Returns (ids_list, error_response)"""
    if not ids_raw or not isinstance(ids_raw, list) or len(ids_raw) == 0:
        return None, jsonify({'success': False, 'message': f'No {entity_name} selected'})

    ids = []
    try:
        for value in ids_raw:
            value_str = str(value)
            for iid in value_str.split(','):
                iid = iid.strip()
                if iid:
                    ids.append(int(iid))
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid {entity_name} IDs: {ids_raw}, error: {e}")
        return None, jsonify({'success': False, 'message': f'Invalid {entity_name} IDs'})

    return list(set(ids)), None  # Remove duplicates

def handle_bulk_operation(zabbix, operation, entity_type, ids, tag_name, tag_value):
    """Handle bulk add/remove operation. Returns JSON response."""
    entity_names = {'host': 'hosts', 'trigger': 'triggers', 'item': 'items'}
    entity_plural = entity_names.get(entity_type, f'{entity_type}s')

    if operation == 'add':
        if entity_type == 'host':
            result = zabbix.bulk_add_tags_detailed(ids, tag_name, tag_value)
        elif entity_type == 'trigger':
            result = zabbix.bulk_add_tags_to_triggers_detailed(ids, tag_name, tag_value)
        elif entity_type == 'item':
            result = zabbix.bulk_add_tags_to_items_detailed(ids, tag_name, tag_value)
        else:
            return jsonify({'success': False, 'message': 'Unknown entity type'})

        message = f'Tag added to {result["success"]} {entity_plural}'
    elif operation == 'remove':
        if entity_type == 'host':
            result = zabbix.bulk_remove_tags_detailed(ids, tag_name)
        elif entity_type == 'trigger':
            result = zabbix.bulk_remove_tags_from_triggers_detailed(ids, tag_name)
        elif entity_type == 'item':
            result = zabbix.bulk_remove_tags_from_items_detailed(ids, tag_name)
        else:
            return jsonify({'success': False, 'message': 'Unknown entity type'})

        message = f'Tag removed from {result["success"]} {entity_plural}'
    else:
        return jsonify({'success': False, 'message': 'Unknown operation'})

    if result['failed'] > 0:
        message += f' ({result["failed"]} failed - likely discovered/read-only)'

    return jsonify({
        'success': True,
        'message': message,
        'details': {
            'success_count': result['success'],
            'failed_count': result['failed'],
            'failed_items': result['errors']
        }
    })

def group_items_by_key(items_data):
    """Group items by key_ for display. Returns (grouped_items, all_hosts)"""
    items_grouped = {}
    all_hosts_dict = {}

    for item in items_data:
        key = item['key_']
        item_hosts = item.get('hosts', [])

        if key not in items_grouped:
            items_grouped[key] = item.copy()
            items_grouped[key]['hosts'] = []
            items_grouped[key]['itemids'] = []
            items_grouped[key]['itemid_host_map'] = {}
            items_grouped[key]['itemid_tags_map'] = {}
            items_grouped[key]['itemid_flags_map'] = {}
            items_grouped[key]['has_discovered'] = False
            items_grouped[key]['all_tags'] = {}

        items_grouped[key]['itemids'].append(item['itemid'])

        for host in item_hosts:
            items_grouped[key]['itemid_host_map'][item['itemid']] = host['hostid']

        item_tags_str = ' '.join([
            f"{tag['tag'].lower()}:{tag.get('value', '').lower()}"
            for tag in item.get('tags', [])
        ])
        items_grouped[key]['itemid_tags_map'][item['itemid']] = item_tags_str

        for tag in item.get('tags', []):
            tag_key = (tag['tag'], tag.get('value', ''))
            if tag_key not in items_grouped[key]['all_tags']:
                items_grouped[key]['all_tags'][tag_key] = 0
            items_grouped[key]['all_tags'][tag_key] += 1

        item_flags = item.get('flags', '0')
        items_grouped[key]['itemid_flags_map'][item['itemid']] = item_flags
        if item_flags == '4':
            items_grouped[key]['has_discovered'] = True

        existing_host_ids = {h['hostid'] for h in items_grouped[key]['hosts']}
        for host in item_hosts:
            if host['hostid'] not in existing_host_ids:
                items_grouped[key]['hosts'].append(host)
                existing_host_ids.add(host['hostid'])
            all_hosts_dict[host['hostid']] = host

    grouped_items = list(items_grouped.values())
    for item in grouped_items:
        item['host_count'] = len(item.get('hosts', []))
        item['tags'] = [
            {'tag': tag_name, 'value': tag_value}
            for (tag_name, tag_value) in sorted(item.get('all_tags', {}).keys())
        ]

    all_hosts = sorted(all_hosts_dict.values(), key=lambda h: h['name'].lower())
    return grouped_items, all_hosts

# Error handler for API endpoints
@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'Internal server error'}), 500
    flash(f'An error occurred: {str(e)}', 'error')
    return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/hosts')
def hosts():
    try:
        # Get per_page parameter for client-side pagination
        per_page = request.args.get('per_page', 100, type=int)

        debug_print("Creating new ZabbixAPI object...")
        zabbix = ZabbixAPI()

        debug_print("Attempting to log in...")
        if not zabbix.authenticate():
            flash('Cannot connect to Zabbix API. Check configuration in .env file', 'error')
            return render_template('hosts.html', hosts=[], per_page=per_page)

        debug_print("Fetching all hosts...")
        hosts_data = zabbix.get_hosts()
        if hosts_data is None:
            flash('Cannot retrieve data from Zabbix API', 'error')
            return render_template('hosts.html', hosts=[], per_page=per_page)

        # Add is_discovered flag for each host
        for host in hosts_data:
            host['is_discovered'] = host.get('flags', '0') == '4'

        debug_print(f"Retrieved {len(hosts_data)} hosts")
        return render_template('hosts.html', hosts=hosts_data, per_page=per_page)
    except Exception as e:
        debug_print(f"Exception in hosts(): {str(e)}")
        flash(f'Error while fetching hosts: {str(e)}', 'error')
        return render_template('hosts.html', hosts=[], per_page=100)

@app.route('/host/<int:host_id>/tags')
def host_tags(host_id):
    try:
        zabbix = ZabbixAPI()
        if not zabbix.authenticate():
            flash('Cannot connect to Zabbix API', 'error')
            return redirect(url_for('hosts'))

        host_info = zabbix.get_host_details(host_id)
        return render_template('host_tags.html', host=host_info)
    except Exception as e:
        flash(f'Error while fetching host tags: {str(e)}', 'error')
        return redirect(url_for('hosts'))

@app.route('/api/host/<int:host_id>/tags', methods=['POST'])
def add_tag(host_id):
    tag_name, tag_value, error = validate_tag_request(request.json)
    if error:
        return error

    zabbix, error = get_authenticated_zabbix()
    if error:
        return error

    result = zabbix.add_tag_to_host(host_id, tag_name, tag_value)
    if result:
        return jsonify({'success': True, 'message': 'Tag has been added'})
    else:
        return jsonify({'success': False, 'message': 'Failed to add tag'})

@app.route('/api/host/<int:host_id>/tags/<tag_name>', methods=['DELETE'])
def remove_tag(host_id, tag_name):
    if not tag_name or tag_name.strip() == '':
        return jsonify({'success': False, 'message': 'Tag name is required'})

    zabbix, error = get_authenticated_zabbix()
    if error:
        return error

    result = zabbix.remove_tag_from_host(host_id, tag_name)
    if result:
        return jsonify({'success': True, 'message': 'Tag has been removed'})
    else:
        return jsonify({'success': False, 'message': 'Failed to remove tag'})

@app.route('/api/hosts/tags/bulk', methods=['POST'])
def bulk_tag_operation():
    tag_name, tag_value, error = validate_tag_request(request.json)
    if error:
        return error

    operation = request.json.get('operation')
    host_ids, error = parse_ids_list(request.json.get('host_ids', []), 'hosts')
    if error:
        return error

    logger.debug(f"Bulk host operation: {operation}, {len(host_ids)} hosts, tag='{tag_name}'")

    zabbix, error = get_authenticated_zabbix()
    if error:
        return error

    return handle_bulk_operation(zabbix, operation, 'host', host_ids, tag_name, tag_value)

# ===============================
# TRIGGER ENDPOINTS
# ===============================

@app.route('/triggers')
def triggers():
    try:
        # Get per_page parameter for client-side pagination
        per_page = request.args.get('per_page', 100, type=int)

        debug_print("Creating new ZabbixAPI object for triggers...")
        zabbix = ZabbixAPI()

        debug_print("Attempting to log in...")
        if not zabbix.authenticate():
            flash('Cannot connect to Zabbix API. Check configuration in .env file', 'error')
            return render_template('triggers.html', triggers=[], per_page=per_page)

        debug_print("Fetching all triggers...")
        triggers_data = zabbix.get_triggers()

        if triggers_data is None:
            flash('Cannot retrieve data from Zabbix API', 'error')
            return render_template('triggers.html', triggers=[], per_page=per_page)

        # Add is_discovered flag for each trigger
        for trigger in triggers_data:
            trigger['is_discovered'] = trigger.get('flags', '0') == '4'

        debug_print(f"Retrieved {len(triggers_data)} triggers")
        return render_template('triggers.html',
                             triggers=triggers_data,
                             per_page=per_page)
    except Exception as e:
        debug_print(f"Exception in triggers(): {str(e)}")
        flash(f'Error while fetching triggers: {str(e)}', 'error')
        return render_template('triggers.html', triggers=[], per_page=100)

@app.route('/trigger/<int:trigger_id>/tags')
def trigger_tags(trigger_id):
    try:
        zabbix = ZabbixAPI()
        if not zabbix.authenticate():
            flash('Cannot connect to Zabbix API', 'error')
            return redirect(url_for('triggers'))

        trigger_info = zabbix.get_trigger_details(trigger_id)
        return render_template('trigger_tags.html', trigger=trigger_info)
    except Exception as e:
        flash(f'Error while fetching trigger tags: {str(e)}', 'error')
        return redirect(url_for('triggers'))

@app.route('/api/trigger/<int:trigger_id>/tags', methods=['POST'])
def add_tag_to_trigger(trigger_id):
    tag_name, tag_value, error = validate_tag_request(request.json)
    if error:
        return error

    zabbix, error = get_authenticated_zabbix()
    if error:
        return error

    result = zabbix.add_tag_to_trigger(trigger_id, tag_name, tag_value)
    if result:
        return jsonify({'success': True, 'message': 'Tag has been added'})
    else:
        return jsonify({'success': False, 'message': 'Failed to add tag'})

@app.route('/api/trigger/<int:trigger_id>/tags/<tag_name>', methods=['DELETE'])
def remove_tag_from_trigger(trigger_id, tag_name):
    if not tag_name or tag_name.strip() == '':
        return jsonify({'success': False, 'message': 'Tag name is required'})

    zabbix, error = get_authenticated_zabbix()
    if error:
        return error

    result = zabbix.remove_tag_from_trigger(trigger_id, tag_name)
    if result:
        return jsonify({'success': True, 'message': 'Tag has been removed'})
    else:
        return jsonify({'success': False, 'message': 'Failed to remove tag'})

@app.route('/api/triggers/tags/bulk', methods=['POST'])
def bulk_trigger_operation():
    tag_name, tag_value, error = validate_tag_request(request.json)
    if error:
        return error

    operation = request.json.get('operation')
    trigger_ids, error = parse_ids_list(request.json.get('trigger_ids', []), 'triggers')
    if error:
        return error

    logger.debug(f"Bulk trigger operation: {operation}, {len(trigger_ids)} triggers, tag='{tag_name}'")

    zabbix, error = get_authenticated_zabbix()
    if error:
        return error

    return handle_bulk_operation(zabbix, operation, 'trigger', trigger_ids, tag_name, tag_value)

# ===============================
# ITEM ENDPOINTS
# ===============================

@app.route('/items')
def items():
    try:
        per_page = request.args.get('per_page', 100, type=int)

        logger.debug("Creating new ZabbixAPI object for items...")
        zabbix = ZabbixAPI()

        if not zabbix.authenticate():
            flash('Cannot connect to Zabbix API. Check configuration in .env file', 'error')
            return render_template('items.html', items=[], all_hosts=[], per_page=per_page)

        logger.debug("Fetching all items...")
        items_data = zabbix.get_items()

        if items_data is None:
            flash('Cannot retrieve data from Zabbix API', 'error')
            return render_template('items.html', items=[], all_hosts=[], per_page=per_page)

        # Group items by key_ using helper function
        grouped_items, all_hosts = group_items_by_key(items_data)

        logger.debug(f"Retrieved {len(items_data)} raw items, grouped into {len(grouped_items)} unique items")
        logger.debug(f"Found {len(all_hosts)} unique hosts")

        return render_template('items.html',
                             items=grouped_items,
                             all_hosts=all_hosts,
                             per_page=per_page)
    except Exception as e:
        logger.error(f"Exception in items(): {str(e)}", exc_info=True)
        flash(f'Error while fetching items: {str(e)}', 'error')
        return render_template('items.html', items=[], all_hosts=[], per_page=100)

@app.route('/item/<int:item_id>/tags')
def item_tags(item_id):
    try:
        zabbix = ZabbixAPI()
        if not zabbix.authenticate():
            flash('Cannot connect to Zabbix API', 'error')
            return redirect(url_for('items'))

        item_info = zabbix.get_item_details(item_id)
        return render_template('item_tags.html', item=item_info)
    except Exception as e:
        flash(f'Error while fetching item tags: {str(e)}', 'error')
        return redirect(url_for('items'))

@app.route('/api/item/<int:item_id>/tags', methods=['POST'])
def add_tag_to_item(item_id):
    tag_name, tag_value, error = validate_tag_request(request.json)
    if error:
        return error

    zabbix, error = get_authenticated_zabbix()
    if error:
        return error

    result = zabbix.add_tag_to_item(item_id, tag_name, tag_value)
    if result:
        return jsonify({'success': True, 'message': 'Tag has been added'})
    else:
        return jsonify({'success': False, 'message': 'Failed to add tag'})

@app.route('/api/item/<int:item_id>/tags/<tag_name>', methods=['DELETE'])
def remove_tag_from_item(item_id, tag_name):
    if not tag_name or tag_name.strip() == '':
        return jsonify({'success': False, 'message': 'Tag name is required'})

    zabbix, error = get_authenticated_zabbix()
    if error:
        return error

    result = zabbix.remove_tag_from_item(item_id, tag_name)
    if result:
        return jsonify({'success': True, 'message': 'Tag has been removed'})
    else:
        return jsonify({'success': False, 'message': 'Failed to remove tag'})

@app.route('/api/items/tags/bulk', methods=['POST'])
def bulk_item_operation():
    tag_name, tag_value, error = validate_tag_request(request.json)
    if error:
        return error

    operation = request.json.get('operation')
    item_ids, error = parse_ids_list(request.json.get('item_ids', []), 'items')
    if error:
        return error

    logger.debug(f"Bulk item operation: {operation}, {len(item_ids)} items, tag='{tag_name}'")

    zabbix, error = get_authenticated_zabbix()
    if error:
        return error

    return handle_bulk_operation(zabbix, operation, 'item', item_ids, tag_name, tag_value)

if __name__ == '__main__':
    # Production mode - debug disabled
    debug_mode = os.getenv('DEBUG_ENABLED', 'false').lower() in ['true', '1', 'yes', 'on']
    app.run(debug=debug_mode, host='0.0.0.0', port=5001)
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from dotenv import load_dotenv
import os
from app.zabbix_api import ZabbixAPI, debug_print

load_dotenv()

app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

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
    try:
        if not request.json:
            return jsonify({'success': False, 'message': 'Invalid request - JSON required'})

        tag_name = request.json.get('tag')
        tag_value = request.json.get('value', '')

        if not tag_name or not isinstance(tag_name, str) or tag_name.strip() == '':
            return jsonify({'success': False, 'message': 'Tag name is required'})

        if len(tag_name) > 255 or (tag_value and len(tag_value) > 255):
            return jsonify({'success': False, 'message': 'Tag name or value too long (max 255 characters)'})

        zabbix = ZabbixAPI()
        if not zabbix.authenticate():
            return jsonify({'success': False, 'message': 'Authorization error'})

        result = zabbix.add_tag_to_host(host_id, tag_name, tag_value)
        if result:
            return jsonify({'success': True, 'message': 'Tag has been added'})
        else:
            return jsonify({'success': False, 'message': 'Failed to add tag'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/host/<int:host_id>/tags/<tag_name>', methods=['DELETE'])
def remove_tag(host_id, tag_name):
    try:
        if not tag_name or tag_name.strip() == '':
            return jsonify({'success': False, 'message': 'Tag name is required'})

        zabbix = ZabbixAPI()
        if not zabbix.authenticate():
            return jsonify({'success': False, 'message': 'Authorization error'})

        result = zabbix.remove_tag_from_host(host_id, tag_name)
        if result:
            return jsonify({'success': True, 'message': 'Tag has been removed'})
        else:
            return jsonify({'success': False, 'message': 'Failed to remove tag'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/hosts/tags/bulk', methods=['POST'])
def bulk_tag_operation():
    try:
        if not request.json:
            debug_print("ERROR: No JSON in request")
            return jsonify({'success': False, 'message': 'Invalid request - JSON required'})

        operation = request.json.get('operation')
        host_ids = request.json.get('host_ids', [])
        tag_name = request.json.get('tag')
        tag_value = request.json.get('value', '')

        debug_print(f"Bulk operation: operation={operation}, host_ids={host_ids}, tag_name='{tag_name}', tag_value='{tag_value}'")

        if not tag_name or not isinstance(tag_name, str) or tag_name.strip() == '':
            debug_print(f"ERROR: Invalid tag_name: '{tag_name}'")
            return jsonify({'success': False, 'message': 'Tag name is required'})

        if not host_ids or not isinstance(host_ids, list) or len(host_ids) == 0:
            debug_print(f"ERROR: No hosts selected: {host_ids}")
            return jsonify({'success': False, 'message': 'No hosts selected'})

        # Convert host_ids to integers
        try:
            host_ids = [int(hid) for hid in host_ids]
        except (ValueError, TypeError) as e:
            debug_print(f"ERROR: Invalid host IDs: {host_ids}, error: {e}")
            return jsonify({'success': False, 'message': 'Invalid host IDs'})

        if len(tag_name) > 255 or (tag_value and len(tag_value) > 255):
            return jsonify({'success': False, 'message': 'Tag name or value too long (max 255 characters)'})

        zabbix = ZabbixAPI()
        if not zabbix.authenticate():
            return jsonify({'success': False, 'message': 'Authorization error'})

        if operation == 'add':
            result = zabbix.bulk_add_tags_detailed(host_ids, tag_name, tag_value)
            message = f'Tag added to {result["success"]} hosts'
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
        elif operation == 'remove':
            result = zabbix.bulk_remove_tags_detailed(host_ids, tag_name)
            message = f'Tag removed from {result["success"]} hosts'
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
        else:
            return jsonify({'success': False, 'message': 'Unknown operation'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

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
    try:
        if not request.json:
            return jsonify({'success': False, 'message': 'Invalid request - JSON required'})

        tag_name = request.json.get('tag')
        tag_value = request.json.get('value', '')

        if not tag_name or not isinstance(tag_name, str) or tag_name.strip() == '':
            return jsonify({'success': False, 'message': 'Tag name is required'})

        if len(tag_name) > 255 or (tag_value and len(tag_value) > 255):
            return jsonify({'success': False, 'message': 'Tag name or value too long (max 255 characters)'})

        zabbix = ZabbixAPI()
        if not zabbix.authenticate():
            return jsonify({'success': False, 'message': 'Authorization error'})

        result = zabbix.add_tag_to_trigger(trigger_id, tag_name, tag_value)
        if result:
            return jsonify({'success': True, 'message': 'Tag has been added'})
        else:
            return jsonify({'success': False, 'message': 'Failed to add tag'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/trigger/<int:trigger_id>/tags/<tag_name>', methods=['DELETE'])
def remove_tag_from_trigger(trigger_id, tag_name):
    try:
        if not tag_name or tag_name.strip() == '':
            return jsonify({'success': False, 'message': 'Tag name is required'})

        zabbix = ZabbixAPI()
        if not zabbix.authenticate():
            return jsonify({'success': False, 'message': 'Authorization error'})

        result = zabbix.remove_tag_from_trigger(trigger_id, tag_name)
        if result:
            return jsonify({'success': True, 'message': 'Tag has been removed'})
        else:
            return jsonify({'success': False, 'message': 'Failed to remove tag'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/triggers/tags/bulk', methods=['POST'])
def bulk_trigger_operation():
    try:
        if not request.json:
            return jsonify({'success': False, 'message': 'Invalid request - JSON required'})

        operation = request.json.get('operation')
        trigger_ids = request.json.get('trigger_ids', [])
        tag_name = request.json.get('tag')
        tag_value = request.json.get('value', '')

        if not tag_name or not isinstance(tag_name, str) or tag_name.strip() == '':
            return jsonify({'success': False, 'message': 'Tag name is required'})

        if not trigger_ids or not isinstance(trigger_ids, list) or len(trigger_ids) == 0:
            return jsonify({'success': False, 'message': 'No triggers selected'})

        # Convert trigger_ids to integers
        try:
            trigger_ids = [int(tid) for tid in trigger_ids]
        except (ValueError, TypeError) as e:
            return jsonify({'success': False, 'message': 'Invalid trigger IDs'})

        if len(tag_name) > 255 or (tag_value and len(tag_value) > 255):
            return jsonify({'success': False, 'message': 'Tag name or value too long (max 255 characters)'})

        zabbix = ZabbixAPI()
        if not zabbix.authenticate():
            return jsonify({'success': False, 'message': 'Authorization error'})

        if operation == 'add':
            result = zabbix.bulk_add_tags_to_triggers_detailed(trigger_ids, tag_name, tag_value)
            message = f'Tag added to {result["success"]} triggers'
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
        elif operation == 'remove':
            result = zabbix.bulk_remove_tags_from_triggers_detailed(trigger_ids, tag_name)
            message = f'Tag removed from {result["success"]} triggers'
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
        else:
            return jsonify({'success': False, 'message': 'Unknown operation'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ===============================
# ITEM ENDPOINTS
# ===============================

@app.route('/items')
def items():
    try:
        # Get per_page parameter for client-side pagination
        per_page = request.args.get('per_page', 100, type=int)

        debug_print("Creating new ZabbixAPI object for items...")
        zabbix = ZabbixAPI()

        debug_print("Attempting to log in...")
        if not zabbix.authenticate():
            flash('Cannot connect to Zabbix API. Check configuration in .env file', 'error')
            return render_template('items.html', items=[], all_hosts=[], per_page=per_page)

        debug_print("Fetching all items...")
        items_data = zabbix.get_items()

        if items_data is None:
            flash('Cannot retrieve data from Zabbix API', 'error')
            return render_template('items.html', items=[], all_hosts=[], per_page=per_page)

        # Group items by key_ (each host has its own itemid for the same template item)
        items_grouped = {}  # {key_: item_data}
        all_hosts_dict = {}  # {hostid: {hostid, name}}

        for item in items_data:
            key = item['key_']
            item_hosts = item.get('hosts', [])

            if key not in items_grouped:
                # First occurrence - create new grouped item
                items_grouped[key] = item.copy()
                items_grouped[key]['hosts'] = []
                items_grouped[key]['itemids'] = []  # Track all itemids for bulk operations
                items_grouped[key]['itemid_host_map'] = {}  # Map itemid -> hostid
                items_grouped[key]['itemid_tags_map'] = {}  # Map itemid -> tags string
                items_grouped[key]['itemid_flags_map'] = {}  # Map itemid -> flags (0=plain, 4=discovered)
                items_grouped[key]['has_discovered'] = False  # Track if any item in group is discovered
                items_grouped[key]['all_tags'] = {}  # Track all unique tags across all items in group {(tag, value): count}

            # Add itemid to the list
            items_grouped[key]['itemids'].append(item['itemid'])

            # Map itemid to its host(s), tags, and flags
            for host in item_hosts:
                items_grouped[key]['itemid_host_map'][item['itemid']] = host['hostid']

            # Store tags for this itemid (as searchable string)
            item_tags_str = ' '.join([
                f"{tag['tag'].lower()}:{tag.get('value', '').lower()}"
                for tag in item.get('tags', [])
            ])
            items_grouped[key]['itemid_tags_map'][item['itemid']] = item_tags_str

            # Collect all unique tags from all items in the group
            for tag in item.get('tags', []):
                tag_key = (tag['tag'], tag.get('value', ''))
                if tag_key not in items_grouped[key]['all_tags']:
                    items_grouped[key]['all_tags'][tag_key] = 0
                items_grouped[key]['all_tags'][tag_key] += 1

            # Store flags (0=plain, 4=discovered)
            item_flags = item.get('flags', '0')
            items_grouped[key]['itemid_flags_map'][item['itemid']] = item_flags
            if item_flags == '4':
                items_grouped[key]['has_discovered'] = True

            # Add hosts to the grouped item (avoid duplicates)
            existing_host_ids = {h['hostid'] for h in items_grouped[key]['hosts']}
            for host in item_hosts:
                if host['hostid'] not in existing_host_ids:
                    items_grouped[key]['hosts'].append(host)
                    existing_host_ids.add(host['hostid'])
                # Track unique hosts for filter dropdown
                all_hosts_dict[host['hostid']] = host

        # Convert to list and add host_count
        grouped_items = list(items_grouped.values())
        for item in grouped_items:
            item['host_count'] = len(item.get('hosts', []))
            # Convert all_tags dict to list of tag objects for template
            # This shows ALL unique tags from ALL items in the group
            item['tags'] = [
                {'tag': tag_name, 'value': tag_value}
                for (tag_name, tag_value) in sorted(item.get('all_tags', {}).keys())
            ]

        # Convert hosts dict to sorted list
        all_hosts = sorted(all_hosts_dict.values(), key=lambda h: h['name'].lower())

        debug_print(f"Retrieved {len(items_data)} raw items, grouped into {len(grouped_items)} unique items")
        debug_print(f"Found {len(all_hosts)} unique hosts")

        return render_template('items.html',
                             items=grouped_items,
                             all_hosts=all_hosts,
                             per_page=per_page)
    except Exception as e:
        debug_print(f"Exception in items(): {str(e)}")
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
    try:
        if not request.json:
            return jsonify({'success': False, 'message': 'Invalid request - JSON required'})

        tag_name = request.json.get('tag')
        tag_value = request.json.get('value', '')

        if not tag_name or not isinstance(tag_name, str) or tag_name.strip() == '':
            return jsonify({'success': False, 'message': 'Tag name is required'})

        if len(tag_name) > 255 or (tag_value and len(tag_value) > 255):
            return jsonify({'success': False, 'message': 'Tag name or value too long (max 255 characters)'})

        zabbix = ZabbixAPI()
        if not zabbix.authenticate():
            return jsonify({'success': False, 'message': 'Authorization error'})

        result = zabbix.add_tag_to_item(item_id, tag_name, tag_value)
        if result:
            return jsonify({'success': True, 'message': 'Tag has been added'})
        else:
            return jsonify({'success': False, 'message': 'Failed to add tag'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/item/<int:item_id>/tags/<tag_name>', methods=['DELETE'])
def remove_tag_from_item(item_id, tag_name):
    try:
        if not tag_name or tag_name.strip() == '':
            return jsonify({'success': False, 'message': 'Tag name is required'})

        zabbix = ZabbixAPI()
        if not zabbix.authenticate():
            return jsonify({'success': False, 'message': 'Authorization error'})

        result = zabbix.remove_tag_from_item(item_id, tag_name)
        if result:
            return jsonify({'success': True, 'message': 'Tag has been removed'})
        else:
            return jsonify({'success': False, 'message': 'Failed to remove tag'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/items/tags/bulk', methods=['POST'])
def bulk_item_operation():
    try:
        if not request.json:
            return jsonify({'success': False, 'message': 'Invalid request - JSON required'})

        operation = request.json.get('operation')
        item_ids_raw = request.json.get('item_ids', [])
        tag_name = request.json.get('tag')
        tag_value = request.json.get('value', '')

        if not tag_name or not isinstance(tag_name, str) or tag_name.strip() == '':
            return jsonify({'success': False, 'message': 'Tag name is required'})

        if not item_ids_raw or not isinstance(item_ids_raw, list) or len(item_ids_raw) == 0:
            return jsonify({'success': False, 'message': 'No items selected'})

        # Parse item_ids - each value can be comma-separated list of itemids (grouped items)
        item_ids = []
        try:
            for value in item_ids_raw:
                value_str = str(value)
                # Split by comma in case of grouped items
                for iid in value_str.split(','):
                    iid = iid.strip()
                    if iid:
                        item_ids.append(int(iid))
        except (ValueError, TypeError) as e:
            return jsonify({'success': False, 'message': f'Invalid item IDs: {str(e)}'})

        # Remove duplicates
        item_ids = list(set(item_ids))

        if len(tag_name) > 255 or (tag_value and len(tag_value) > 255):
            return jsonify({'success': False, 'message': 'Tag name or value too long (max 255 characters)'})

        debug_print(f"Bulk operation '{operation}' on {len(item_ids)} unique items: tag='{tag_name}'")

        zabbix = ZabbixAPI()
        if not zabbix.authenticate():
            return jsonify({'success': False, 'message': 'Authorization error'})

        if operation == 'add':
            result = zabbix.bulk_add_tags_to_items_detailed(item_ids, tag_name, tag_value)
            message = f'Tag added to {result["success"]} items'
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
        elif operation == 'remove':
            result = zabbix.bulk_remove_tags_from_items_detailed(item_ids, tag_name)
            message = f'Tag removed from {result["success"]} items'
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
        else:
            return jsonify({'success': False, 'message': 'Unknown operation'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    # Production mode - debug disabled
    debug_mode = os.getenv('DEBUG_ENABLED', 'false').lower() in ['true', '1', 'yes', 'on']
    app.run(debug=debug_mode, host='0.0.0.0', port=5001)
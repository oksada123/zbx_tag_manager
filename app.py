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
        debug_print("Creating new ZabbixAPI object...")
        zabbix = ZabbixAPI()

        debug_print("Attempting to log in...")
        if not zabbix.authenticate():
            flash('Cannot connect to Zabbix API. Check configuration in .env file', 'error')
            return render_template('hosts.html', hosts=[])

        debug_print("Fetching list of hosts...")
        hosts_data = zabbix.get_hosts()
        if hosts_data is None:
            flash('Cannot retrieve data from Zabbix API', 'error')
            return render_template('hosts.html', hosts=[])

        debug_print(f"Retrieved {len(hosts_data)} hosts")
        return render_template('hosts.html', hosts=hosts_data)
    except Exception as e:
        debug_print(f"Exception in hosts(): {str(e)}")
        flash(f'Error while fetching hosts: {str(e)}', 'error')
        return render_template('hosts.html', hosts=[])

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
        tag_name = request.json.get('tag')
        tag_value = request.json.get('value', '')

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
        operation = request.json.get('operation')
        host_ids = request.json.get('host_ids', [])
        tag_name = request.json.get('tag')
        tag_value = request.json.get('value', '')

        zabbix = ZabbixAPI()
        if not zabbix.authenticate():
            return jsonify({'success': False, 'message': 'Authorization error'})

        if operation == 'add':
            success_count = zabbix.bulk_add_tags(host_ids, tag_name, tag_value)
            return jsonify({
                'success': True,
                'message': f'Tag added to {success_count} hosts'
            })
        elif operation == 'remove':
            success_count = zabbix.bulk_remove_tags(host_ids, tag_name)
            return jsonify({
                'success': True,
                'message': f'Tag removed from {success_count} hosts'
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
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 100, type=int)  # 100 triggers per page

        debug_print("Creating new ZabbixAPI object for triggers...")
        zabbix = ZabbixAPI()

        debug_print("Attempting to log in...")
        if not zabbix.authenticate():
            flash('Cannot connect to Zabbix API. Check configuration in .env file', 'error')
            return render_template('triggers.html', triggers=[], total_count=0, page=1, per_page=per_page, total_pages=1)

        debug_print("Fetching number of triggers...")
        total_count = zabbix.get_triggers_count()
        debug_print(f"Total number of triggers: {total_count}")

        if total_count == 0:
            return render_template('triggers.html', triggers=[], total_count=0, page=1, per_page=per_page, total_pages=1)

        # Calculate pagination
        total_pages = (total_count + per_page - 1) // per_page
        offset = (page - 1) * per_page

        debug_print(f"Fetching triggers: page {page}/{total_pages}, offset {offset}, limit {per_page}...")
        triggers_data = zabbix.get_triggers(limit=per_page, offset=offset)

        if triggers_data is None:
            flash('Cannot retrieve data from Zabbix API', 'error')
            return render_template('triggers.html', triggers=[], total_count=0, page=1, per_page=per_page, total_pages=1)

        debug_print(f"Retrieved {len(triggers_data)} triggers for page {page}")
        return render_template('triggers.html',
                             triggers=triggers_data,
                             total_count=total_count,
                             page=page,
                             per_page=per_page,
                             total_pages=total_pages)
    except Exception as e:
        debug_print(f"Exception in triggers(): {str(e)}")
        flash(f'Error while fetching triggers: {str(e)}', 'error')
        return render_template('triggers.html', triggers=[], total_count=0, page=1, per_page=100, total_pages=1)

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
        tag_name = request.json.get('tag')
        tag_value = request.json.get('value', '')

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
        operation = request.json.get('operation')
        trigger_ids = request.json.get('trigger_ids', [])
        tag_name = request.json.get('tag')
        tag_value = request.json.get('value', '')

        zabbix = ZabbixAPI()
        if not zabbix.authenticate():
            return jsonify({'success': False, 'message': 'Authorization error'})

        if operation == 'add':
            success_count = zabbix.bulk_add_tags_to_triggers(trigger_ids, tag_name, tag_value)
            return jsonify({
                'success': True,
                'message': f'Tag added to {success_count} triggers'
            })
        elif operation == 'remove':
            success_count = zabbix.bulk_remove_tags_from_triggers(trigger_ids, tag_name)
            return jsonify({
                'success': True,
                'message': f'Tag removed from {success_count} triggers'
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
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 100, type=int)  # 100 items per page

        debug_print("Creating new ZabbixAPI object for items...")
        zabbix = ZabbixAPI()

        debug_print("Attempting to log in...")
        if not zabbix.authenticate():
            flash('Cannot connect to Zabbix API. Check configuration in .env file', 'error')
            return render_template('items.html', items=[], total_count=0, page=1, per_page=per_page, total_pages=1)

        debug_print("Fetching number of items...")
        total_count = zabbix.get_items_count()
        debug_print(f"Total number of items: {total_count}")

        if total_count == 0:
            return render_template('items.html', items=[], total_count=0, page=1, per_page=per_page, total_pages=1)

        # Calculate pagination
        total_pages = (total_count + per_page - 1) // per_page
        offset = (page - 1) * per_page

        debug_print(f"Fetching items: page {page}/{total_pages}, offset {offset}, limit {per_page}...")
        items_data = zabbix.get_items(limit=per_page, offset=offset)

        if items_data is None:
            flash('Cannot retrieve data from Zabbix API', 'error')
            return render_template('items.html', items=[], total_count=0, page=1, per_page=per_page, total_pages=1)

        debug_print(f"Retrieved {len(items_data)} items for page {page}")
        return render_template('items.html',
                             items=items_data,
                             total_count=total_count,
                             page=page,
                             per_page=per_page,
                             total_pages=total_pages)
    except Exception as e:
        debug_print(f"Exception in items(): {str(e)}")
        flash(f'Error while fetching items: {str(e)}', 'error')
        return render_template('items.html', items=[], total_count=0, page=1, per_page=100, total_pages=1)

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
        tag_name = request.json.get('tag')
        tag_value = request.json.get('value', '')

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
        operation = request.json.get('operation')
        item_ids = request.json.get('item_ids', [])
        tag_name = request.json.get('tag')
        tag_value = request.json.get('value', '')

        zabbix = ZabbixAPI()
        if not zabbix.authenticate():
            return jsonify({'success': False, 'message': 'Authorization error'})

        if operation == 'add':
            success_count = zabbix.bulk_add_tags_to_items(item_ids, tag_name, tag_value)
            return jsonify({
                'success': True,
                'message': f'Tag added to {success_count} items'
            })
        elif operation == 'remove':
            success_count = zabbix.bulk_remove_tags_from_items(item_ids, tag_name)
            return jsonify({
                'success': True,
                'message': f'Tag removed from {success_count} items'
            })
        else:
            return jsonify({'success': False, 'message': 'Unknown operation'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
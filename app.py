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
        debug_print("Tworzę nowy obiekt ZabbixAPI...")
        zabbix = ZabbixAPI()

        debug_print("Próbuję się zalogować...")
        if not zabbix.authenticate():
            flash('Nie można połączyć się z Zabbix API. Sprawdź konfigurację w pliku .env', 'error')
            return render_template('hosts.html', hosts=[])

        debug_print("Pobieram listę hostów...")
        hosts_data = zabbix.get_hosts()
        if hosts_data is None:
            flash('Nie można pobrać danych z Zabbix API', 'error')
            return render_template('hosts.html', hosts=[])

        debug_print(f"Pobrano {len(hosts_data)} hostów")
        return render_template('hosts.html', hosts=hosts_data)
    except Exception as e:
        debug_print(f"Exception w hosts(): {str(e)}")
        flash(f'Błąd podczas pobierania hostów: {str(e)}', 'error')
        return render_template('hosts.html', hosts=[])

@app.route('/host/<int:host_id>/tags')
def host_tags(host_id):
    try:
        zabbix = ZabbixAPI()
        if not zabbix.authenticate():
            flash('Nie można połączyć się z Zabbix API', 'error')
            return redirect(url_for('hosts'))

        host_info = zabbix.get_host_details(host_id)
        return render_template('host_tags.html', host=host_info)
    except Exception as e:
        flash(f'Błąd podczas pobierania tagów hosta: {str(e)}', 'error')
        return redirect(url_for('hosts'))

@app.route('/api/host/<int:host_id>/tags', methods=['POST'])
def add_tag(host_id):
    try:
        tag_name = request.json.get('tag')
        tag_value = request.json.get('value', '')

        zabbix = ZabbixAPI()
        if not zabbix.authenticate():
            return jsonify({'success': False, 'message': 'Błąd autoryzacji'})

        result = zabbix.add_tag_to_host(host_id, tag_name, tag_value)
        if result:
            return jsonify({'success': True, 'message': 'Tag został dodany'})
        else:
            return jsonify({'success': False, 'message': 'Nie udało się dodać tagu'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/host/<int:host_id>/tags/<tag_name>', methods=['DELETE'])
def remove_tag(host_id, tag_name):
    try:
        zabbix = ZabbixAPI()
        if not zabbix.authenticate():
            return jsonify({'success': False, 'message': 'Błąd autoryzacji'})

        result = zabbix.remove_tag_from_host(host_id, tag_name)
        if result:
            return jsonify({'success': True, 'message': 'Tag został usunięty'})
        else:
            return jsonify({'success': False, 'message': 'Nie udało się usunąć tagu'})
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
            return jsonify({'success': False, 'message': 'Błąd autoryzacji'})

        if operation == 'add':
            success_count = zabbix.bulk_add_tags(host_ids, tag_name, tag_value)
            return jsonify({
                'success': True,
                'message': f'Tag dodany do {success_count} hostów'
            })
        elif operation == 'remove':
            success_count = zabbix.bulk_remove_tags(host_ids, tag_name)
            return jsonify({
                'success': True,
                'message': f'Tag usunięty z {success_count} hostów'
            })
        else:
            return jsonify({'success': False, 'message': 'Nieznana operacja'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ===============================
# ENDPOINTY DLA TRIGGERÓW
# ===============================

@app.route('/triggers')
def triggers():
    try:
        # Pobierz parametry paginacji
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 100, type=int)  # 100 triggerów na stronę

        debug_print("Tworzę nowy obiekt ZabbixAPI dla triggerów...")
        zabbix = ZabbixAPI()

        debug_print("Próbuję się zalogować...")
        if not zabbix.authenticate():
            flash('Nie można połączyć się z Zabbix API. Sprawdź konfigurację w pliku .env', 'error')
            return render_template('triggers.html', triggers=[], total_count=0, page=1, per_page=per_page, total_pages=1)

        debug_print("Pobieram liczbę triggerów...")
        total_count = zabbix.get_triggers_count()
        debug_print(f"Łączna liczba triggerów: {total_count}")

        if total_count == 0:
            return render_template('triggers.html', triggers=[], total_count=0, page=1, per_page=per_page, total_pages=1)

        # Oblicz paginację
        total_pages = (total_count + per_page - 1) // per_page
        offset = (page - 1) * per_page

        debug_print(f"Pobieram triggery: strona {page}/{total_pages}, offset {offset}, limit {per_page}...")
        triggers_data = zabbix.get_triggers(limit=per_page, offset=offset)

        if triggers_data is None:
            flash('Nie można pobrać danych z Zabbix API', 'error')
            return render_template('triggers.html', triggers=[], total_count=0, page=1, per_page=per_page, total_pages=1)

        debug_print(f"Pobrano {len(triggers_data)} triggerów dla strony {page}")
        return render_template('triggers.html',
                             triggers=triggers_data,
                             total_count=total_count,
                             page=page,
                             per_page=per_page,
                             total_pages=total_pages)
    except Exception as e:
        debug_print(f"Exception w triggers(): {str(e)}")
        flash(f'Błąd podczas pobierania triggerów: {str(e)}', 'error')
        return render_template('triggers.html', triggers=[], total_count=0, page=1, per_page=100, total_pages=1)

@app.route('/trigger/<int:trigger_id>/tags')
def trigger_tags(trigger_id):
    try:
        zabbix = ZabbixAPI()
        if not zabbix.authenticate():
            flash('Nie można połączyć się z Zabbix API', 'error')
            return redirect(url_for('triggers'))

        trigger_info = zabbix.get_trigger_details(trigger_id)
        return render_template('trigger_tags.html', trigger=trigger_info)
    except Exception as e:
        flash(f'Błąd podczas pobierania tagów triggera: {str(e)}', 'error')
        return redirect(url_for('triggers'))

@app.route('/api/trigger/<int:trigger_id>/tags', methods=['POST'])
def add_tag_to_trigger(trigger_id):
    try:
        tag_name = request.json.get('tag')
        tag_value = request.json.get('value', '')

        zabbix = ZabbixAPI()
        if not zabbix.authenticate():
            return jsonify({'success': False, 'message': 'Błąd autoryzacji'})

        result = zabbix.add_tag_to_trigger(trigger_id, tag_name, tag_value)
        if result:
            return jsonify({'success': True, 'message': 'Tag został dodany'})
        else:
            return jsonify({'success': False, 'message': 'Nie udało się dodać tagu'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/trigger/<int:trigger_id>/tags/<tag_name>', methods=['DELETE'])
def remove_tag_from_trigger(trigger_id, tag_name):
    try:
        zabbix = ZabbixAPI()
        if not zabbix.authenticate():
            return jsonify({'success': False, 'message': 'Błąd autoryzacji'})

        result = zabbix.remove_tag_from_trigger(trigger_id, tag_name)
        if result:
            return jsonify({'success': True, 'message': 'Tag został usunięty'})
        else:
            return jsonify({'success': False, 'message': 'Nie udało się usunąć tagu'})
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
            return jsonify({'success': False, 'message': 'Błąd autoryzacji'})

        if operation == 'add':
            success_count = zabbix.bulk_add_tags_to_triggers(trigger_ids, tag_name, tag_value)
            return jsonify({
                'success': True,
                'message': f'Tag dodany do {success_count} triggerów'
            })
        elif operation == 'remove':
            success_count = zabbix.bulk_remove_tags_from_triggers(trigger_ids, tag_name)
            return jsonify({
                'success': True,
                'message': f'Tag usunięty z {success_count} triggerów'
            })
        else:
            return jsonify({'success': False, 'message': 'Nieznana operacja'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
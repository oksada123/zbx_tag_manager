# Zabbix Tag Manager

Web application for managing tags on hosts, triggers, and items in Zabbix 7.

## Requirements

- Python 3.8+
- Zabbix Server 7.x with API enabled

## Installation

1. Install dependencies:
```bash
./install.sh
```

2. Configure environment variables:
```bash
cp .env.example .env
nano .env
```

Edit `.env` file with your Zabbix credentials:
```
ZABBIX_URL=http://your-zabbix-server/api_jsonrpc.php
ZABBIX_USER=your-username
ZABBIX_PASSWORD=your-password
SECRET_KEY=your-secret-key-here
```

## Running

```bash
./run.sh
```

Application will be available at: http://localhost:5000

## License

MIT License

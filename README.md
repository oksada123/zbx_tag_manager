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

Edit `.env` file with your Zabbix configuration:

### Option 1: API Token (Recommended)
```
ZABBIX_URL=http://your-zabbix-server/api_jsonrpc.php
ZABBIX_API_TOKEN=your-api-token-here
SECRET_KEY=your-secret-key-here
```

To generate an API token in Zabbix:
1. Go to User settings (top right corner) -> API tokens
2. Click "Create API token"
3. Set name and expiration date
4. Copy the generated token

### Option 2: Username/Password (Fallback)
```
ZABBIX_URL=http://your-zabbix-server/api_jsonrpc.php
ZABBIX_USER=your-username
ZABBIX_PASSWORD=your-password
SECRET_KEY=your-secret-key-here
```

**Note:** If both API token and username/password are configured, the API token takes priority.

## Running

```bash
./run.sh
```

Application will be available at: http://localhost:5000

## License

MIT License

module.exports = {
  apps: [{
    name: 'backrest-mcp',
    script: 'python3',
    args: ['-m', 'backrest_mcp.server'],
    cwd: '/home/ted/repos/personal/backrest-mcp',
    interpreter: 'none',
    autorestart: true,
    watch: false,
    env: {
      BACKREST_URL: 'http://localhost:9898',
      // Safety controls — restrictive defaults, override explicitly to enable writes
      BACKREST_READONLY: 'true',
      BACKREST_ALLOW_DESTRUCTIVE: 'false',
      BACKREST_RESTORE_ALLOWED_PREFIX: '/tmp/backrest-restore/',
      BACKREST_AUDIT_LOG: '/home/ted/logs/backrest-mcp-audit.jsonl',
      LOG_LEVEL: 'INFO',
      LOG_FILE: '/home/ted/logs/backrest-mcp.log',
      // BACKREST_USERNAME, BACKREST_PASSWORD injected via:
      // pm2 start ecosystem.config.js --env-file ~/.secrets/forge.env
    },
  }],
};

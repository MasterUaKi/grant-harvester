module.exports = {
  apps: [
    {
      name: "grant-harvester",
      script: "main.py",
      interpreter: "C:\\Entwiklung\\grant-harvester\\.venv\\Scripts\\python.exe",
      cwd: "C:\\Entwiklung\\grant-harvester",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "450M",
      env: {
        PYTHONUNBUFFERED: "1",
        PYTHONIOENCODING: "utf-8"
      },
      error_file: "logs\\err.log",
      out_file: "logs\\out.log",
      log_date_format: "YYYY-MM-DD HH:mm:ss"
    }
  ]
};

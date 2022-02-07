module.exports = {
  apps : [{
          name: "webhook",
          script: "/usr/bin/webhook",
          cwd: "/opt/undp_bougainville",
          args: "-hooks hooks.json -verbose -secure -cert /home/cam/fullchain.pem -key /home/cam/privkey.pem",
          env: {
            "MACHINE": "development"
          },
         env_production: {
            "MACHINE": "production",
         }
  }]
};

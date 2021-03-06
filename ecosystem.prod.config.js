module.exports = {
  apps : [{
          name: "webhook",
          script: "/usr/bin/webhook",
          cwd: "/opt/undp_bougainville",
          args: "-hooks hooks.json -verbose -secure -cert /home/undp/fullchain.pem -key /home/undp/privkey.pem",
          env: {
            "MACHINE": "development"
          },
         env_production: {
            "MACHINE": "production",
         }
  }]
};

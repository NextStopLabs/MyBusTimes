module.exports = {
    apps: [
        {
            name: "django-api",
            script: "./start-django.sh",
            interpreter: "bash"
        },
        {
            name: "node-server",
            script: "index.js",
            interpreter: "node"
        }
    ]
};

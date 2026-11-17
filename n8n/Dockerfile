# Railway (эсвэл бусад PaaS) дээр n8n: асахдаа credential + workflow-уудыг импортлоод n8n-ийг эхлүүлнэ.
# Локалд docker-compose.yml-ийн n8n-init + n8n хоёр service үүнийг хийдэг.
FROM n8nio/n8n:2.48.4
COPY --chown=node:node n8n /bootstrap
ENTRYPOINT ["/bin/sh", "-c", "sh /bootstrap/init.sh && exec n8n start"]

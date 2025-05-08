FROM nginx:alpine

# Install curl for health check
RUN apk --no-cache add curl

# Copy the HTML file to nginx's serving directory
COPY index.html /usr/share/nginx/html/index.html

# Create a simple favicon.ico file to avoid 404 errors
RUN touch /usr/share/nginx/html/favicon.ico

# Create nginx configuration with CORS settings
RUN echo 'server { \
    listen 80; \
    server_name localhost; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ =404; \
        add_header "Access-Control-Allow-Origin" "*"; \
    } \
}' > /etc/nginx/conf.d/default.conf

# Healthcheck to verify nginx is running
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
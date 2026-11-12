# Gitea for Railway. Compose runs the stock image and a separate init container that shares its
# volume; Railway cannot share a volume between services, so this image creates the accounts itself.
FROM gitea/gitea:1.24.6

COPY bootstrap.sh /usr/local/bin/bootstrap.sh
RUN chmod +x /usr/local/bin/bootstrap.sh

ENTRYPOINT ["/usr/local/bin/bootstrap.sh"]

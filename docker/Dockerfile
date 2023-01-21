FROM python:3.10-rc-slim-bullseye

RUN python -m pip install --upgrade pip

RUN apt-get update && \
    apt-get install -yq tzdata && \
    ln -fs /usr/share/zoneinfo/Europe/Moscow /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata


RUN apt-get update && apt-get install -y wget
COPY --chown=www-data:www-data analytics_service/app/build/requirements.txt var/app/build/requirements.txt


RUN pip install -r var/app/build/requirements.txt
ENV DOCKERIZE_VERSION v0.6.1
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && rm dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

VOLUME /var
EXPOSE $APP_PORT_ANALYTICS
WORKDIR /var/app/
COPY --chown=www-data:www-data analytics_service/docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
CMD ["/entrypoint.sh"]
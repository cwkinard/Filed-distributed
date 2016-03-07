FROM resin/rpi-raspbian:jessie 

MAINTAINER Will Kinard "wilsonkinard@gmail.com"

# Management
EXPOSE  15672
# Rabbitmq
EXPOSE 5672

RUN apt-get update && apt-get install -y \
    rabbitmq-server

# Enable plugins
RUN rabbitmq-plugins enable rabbitmq_management

# Configure rabbitmq
COPY ["rabbitmq-env.conf", "/etc/rabbitmq/rabbitmq-env.conf"]
RUN chmod 755 /etc/rabbitmq/rabbitmq-env.conf

# Create users for the apps
COPY ["rabbitmq-setup.sh", "/tmp/rabbitmq/rabbitmq-setup.sh"]
RUN service rabbitmq-server start && \
sh /tmp/rabbitmq/rabbitmq-setup.sh && \
rm /tmp/rabbitmq/rabbitmq-setup.sh && \
service rabbitmq-server stop

# start rabbitmq
USER rabbitmq
CMD ["rabbitmq-server", "start"]



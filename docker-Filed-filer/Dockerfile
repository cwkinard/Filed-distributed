FROM resin/rpi-raspbian:jessie
MAINTAINER Will Kinard "wilsonkinard@gmail.com"



RUN apt-get update && apt-get install -y \
        python \
        python-dev \
        python-distribute \
        python-pip \
        git-core \
	netcat 

RUN mkdir Filed 

WORKDIR /Filed

# Create necessary directories
RUN mkdir tmp && mkdir logs

# Copy in code and sensitive files and directories
COPY requirements.txt requirements.txt
COPY start.sh start.sh

# Install our requirements
RUN pip install -r requirements.txt

# Set time zone
RUN cp /usr/share/zoneinfo/America/New_York /etc/localtime

RUN chmod 755 start.sh

# Do the magic
CMD ["/Filed/start.sh"]

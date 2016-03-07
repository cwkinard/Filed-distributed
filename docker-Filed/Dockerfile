FROM resin/rpi-raspbian:jessie
MAINTAINER Will Kinard "wilsonkinard@gmail.com"


RUN apt-get -y update && \
    apt-get install python-pip

#COPY Filed.py Filed.py
COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt && \
    mkdir logs && \
    cp /usr/share/zoneinfo/America/New_York /etc/localtime

ENTRYPOINT ["python", "-u", "Filed.py"]

FROM debian:sid
MAINTAINER xarthisius.kk@gmail.com

ENV JENKINS_TOKEN=foo JENKINS_URL="https://tests.yt-project.org"

RUN apt-get update -qy && \
  apt-get install -qy python-hglib python-tornado python-requests \
    python-setuptools curl unzip && \
  cd /tmp && \
  curl -OL https://github.com/matiasb/python-unidiff/archive/master.zip && \
  unzip master.zip && \
  cd python-unidiff-master && \
  python2 setup.py install && \
  cd /tmp && \
  rm -rf *.zip python-unidiff-master && \
  apt-get remove -qy curl unzip && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

RUN cd /srv && \
  hg clone https://bitbucket.org/xarthisius/fido-prhandler prhandler

EXPOSE 8888
WORKDIR /srv/prhandler
CMD ["python2", "main.py"]

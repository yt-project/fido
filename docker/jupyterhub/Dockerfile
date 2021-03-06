FROM jupyter/jupyterhub

ENV BITBUCKET_CLIENT_ID=github_id BITBUCKET_CLIENT_SECRET=github_secret \
  OAUTH_CALLBACK_URL=https://example.com/hub/oauth_callback \
  CONFIGPROXY_AUTH_TOKEN=super-secret DOCKER_HOST=tcp://141.142.234.27:2375

VOLUME ["/srv/jupyterhub/ssl", "/var/run/jupyterhub"]
EXPOSE 443

RUN apt-get install -y libpq-dev mercurial sssd libpam-sss libnss-sss supervisor

RUN pip3 install git+git://github.com/jupyter/dockerspawner.git
RUN pip3 install git+git://github.com/jupyter/oauthenticator.git
RUN pip3 install hg+https://bitbucket.org/MatthewTurk/ythubspawner
RUN pip3 install dateutils

# set working directory to the jupyterhub directory
WORKDIR /srv/jupyterhub

ADD sssd.conf /etc/sssd/sssd.conf
RUN chmod 0600 /etc/sssd/sssd.conf && chown root:root /etc/sssd/sssd.conf
ADD supervisord.conf /etc/supervisor/supervisord.conf
ADD jupyterhub.conf /etc/supervisor/conf.d/jupyterhub.conf
ADD cull_idle_servers.py /srv/jupyterhub/cull_idle_servers.py

CMD ["supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]

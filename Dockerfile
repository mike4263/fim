#https://pythonspeed.com/articles/base-image-python-docker-images/
FROM fedora:35
COPY . /app

RUN dnf install -y python3 pipenv which
RUN cd /app && pipenv install --deploy --ignore-pipfile \
    && mkdir -p /var/fim/

WORKDIR /app
ENTRYPOINT ["pipenv", "run", "python", "fim.py"] 

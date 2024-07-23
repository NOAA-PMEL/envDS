# FROM python:3.10-slim
FROM python:3.12-slim-bullseye

RUN groupadd  dashboard
RUN useradd -m -g dashboard -s /bin/bash dashboard

# WORKDIR /app
ENV APP_HOME=/app
WORKDIR $APP_HOME

# RUN apt update && apt -y install xmlstarlet

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY lib/. /lib
RUN pip3 install --no-index --find-links=/lib/envds envds
#
COPY VERSION .

# COPY datasets.d.sh .
# RUN chmod +x datasets.d.sh

COPY dashapp ./dashapp
# COPY ./envds_dashboard_tmp.py ./dashboard.py
# COPY ./main_tmp.py main.py
COPY ./envds_dashboard.py ./envds_dashboard.py
COPY ./main.py main.py
#
# run the same as tomcat so we can update the erddap datasets for now
RUN chown -R dashboard:dashboard $APP_HOME
USER dashboard

# CMD [ "python", "app.py" ]
# CMD exec gunicorn --workers 1 --threads 8 --timeout 0 -b 0.0.0.0:8000 app:server
# CMD ["python", "dashboard.py"]
CMD ["python", "envds_dashboard.py"]

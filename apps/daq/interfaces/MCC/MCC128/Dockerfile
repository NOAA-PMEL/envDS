# FROM python:3.11-bullseye
#FROM python:3.4
FROM ubuntu:20.04 

# Allow statements and log messages to immediately appear in the Knative logs
#ENV PYTHONUNBUFFERED True
ENV DEBIAN_FRONTEND=noninteractive 

RUN apt-get update \
    # apt-get install -y --no-install-recommends make \
    # && apt-get install -y --no-install-recommends gcc \
    && apt-get -y install build-essential \
    && apt-get install -y libraspberrypi-dev \
    && apt-get install -y kmod \
    && apt-get install -y i2c-tools

# RUN apt-get install -y python3 \
#     && apt install -y python3-pip
#     #apt-get install -y --no-install-recommends python3
    #apt-get install -y libraspberrypi-dev raspberrypi-kernel-headers
#RUN apt update && apt upgrade -y
RUN apt-get install -y software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt install python3.10 -y
# RUN apt install python3.11-pip -y
RUN apt install -y curl python3.10-distutils
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10
#RUN apt install make && apt install gcc
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1

#RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1
#RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.4 1
#RUN update-alternatives --set python /usr/bin/python3.4
#RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.6 1

#RUN apt install python3-pip -y
#RUN python -m pip install --upgrade pip

WORKDIR /app
ADD ./mfg/daqhats ./daqhats
# ADD ./mfg/daqhats.tar.gz ./daqhats.tar.gz
# RUN ls
# RUN tar -zxf daqhats.tar.gz
# RUN rm daqhats.tar.gz

RUN cd daqhats \
    && make -C lib all \
    && make -C lib install \
    && make -C lib clean \
    && make -C tools all \
    && make -C tools install \
    && make -C tools clean

RUN cd daqhats && python3.10 -m pip wheel .
RUN cd daqhats && python3.10 -m pip install .

# RUN cd daqhats && \
#     ./install.sh


# FROM python:3.10-slim
ENV PYTHONUNBUFFERED True

ENV APP_HOME /app
WORKDIR $APP_HOME

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY lib/. /lib

RUN pip3 install --no-index --find-links=/lib/envds envds

COPY ./mcc_client.py .
COPY ./mcc128.py .

# WORKDIR /app
# COPY --from=builder /app/daqhats/daqhats-1.4.0.6-py3-none-any.whl ./lib/daqhats-1.4.0.6-py3-none-any.whl
# COPY --from=builder /usr/local/lib/libdaqhats.so.1.4.0.6 /usr/local/lib/libdaqhats.so.1.4.0.6
# RUN ln -sf /usr/local/lib/libdaqhats.so.1.4.0.6 /usr/local/lib/libdaqhats.so.1
# RUN ln -sf /usr/local/lib/libdaqhats.so.1.4.0.6 /usr/local/lib/libdaqhats.so

CMD ["python", "mcc128.py", "--host", "0.0.0.0"]

FROM python:3.6-slim

WORKDIR /app

# prerequisites
COPY lib/phyml lib/phyml

# packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# src files
COPY src/aws.py src/modeltest.py src/dockerentrypoint.py ./

# execution
ENTRYPOINT [ "python3", "dockerentrypoint.py" ]
CMD [ "Ref::path". "Ref:cmd", "Ref::jmodeltestrunid", "Ref::sourcerequestid" ]

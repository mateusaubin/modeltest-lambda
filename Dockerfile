FROM python:3.6-slim

WORKDIR /app

# prerequisites
COPY lib/phyml lib/phyml

# packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# src files
COPY aws.py handler.py dockerentrypoint.py ./

# execution
ENTRYPOINT [ "python3", "dockerentrypoint.py" ]
CMD [ "Ref::path". "Ref:cmd", "Ref::jmodeltestrunid" ]

# docker run -it mateusaubin/modeltest-lambda \
# "mestrado-dev-phyml://#_src/primate-mtDNA.phy" \
# "-d nt -n 1 -b 0 --run_id GTR+I+G -m 012345 -f m -v e -c 4 -a e --no_memory_check --r_seed 12345 -o tlr -s BEST" \
# "docker-run"

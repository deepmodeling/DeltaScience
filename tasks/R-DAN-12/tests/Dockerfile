FROM registry.dp.tech/public/pkscience-r-dan-12-agent@sha256:b78f3de7e7b679f60c657e54e46efd28efa768ea7fb8cc2e9d4115a562870868
COPY . /tests/
COPY runner/test.sh /tests/test.sh
COPY public-task/task.json /workspace/task/task.json
RUN chmod -R a-w /tests /workspace/task
ENV RETRO_ROLE=verifier RETRO_SERVICE_BINDING_SOURCE=/run/retro-platform/service.json

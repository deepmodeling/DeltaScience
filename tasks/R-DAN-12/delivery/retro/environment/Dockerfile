FROM registry.dp.tech/public/pkscience-r-dan-12-agent@sha256:b78f3de7e7b679f60c657e54e46efd28efa768ea7fb8cc2e9d4115a562870868
ARG RETRO_ACTIVE_VARIANT=open
COPY views/${RETRO_ACTIVE_VARIANT} /workspace/task
COPY materialize_task.py /opt/retro/materialize_task.py
RUN python /opt/retro/materialize_task.py && chmod -R a-w /workspace/task
COPY retro-native/cleanup_agent_view_v17.py /opt/retro/cleanup_agent_view_v17.py
RUN python -I -B /opt/retro/cleanup_agent_view_v17.py

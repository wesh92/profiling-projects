from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from src.profile import Profile

profile = Profile(tracemalloc_enabled=True, cprofile_enabled=True)

class ProfiledKubernetesPodOperator(KubernetesPodOperator):
    """
    A subclassed version of the KubernetesPodOperator
    that includes deep profiling statistics.
    """

    @profile
    def execute(self, context):
        return super().execute(context)

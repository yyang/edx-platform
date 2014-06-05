"""
Check code quality using pep8, pylint, and diff_quality.
"""

import os
from invoke import Collection
from invoke import task
from invoke import run as sh

from .utils.envs import Env


@task('prereqs.install',
    help={
        "system": "System to act on",
        "errors": "Check for errors only"
    }
)
def pylint(system="lms,cms,common", errors=False, **kwargs):
    """
    Run pylint on system code
    """
    if system:
        systems = system.split(',')
    else:
        systems = ['lms', 'cms']

    for system in systems:
        # Directory to put the pylint report in.
        # This makes the folder if it doesn't already exist.
        report_dir = Env.REPORT_ROOT / system
        report_dir.makedirs_p()

        flags = '-E' if errors else ''

        apps = [system]

        for directory in ['djangoapps', 'lib']:
            dirs = os.listdir(os.path.join(system, directory))
            apps.extend([d for d in dirs if os.path.isdir(os.path.join(system, directory, d))])

        apps_list = ' '.join(apps)

        pythonpath_prefix = (
            "PYTHONPATH={system}:{system}/djangoapps:{system}/"
            "lib:common/djangoapps:common/lib".format(
                system=system
            )
        )

        sh(
            "{pythonpath_prefix} pylint {flags} -f parseable {apps} | "
            "tee {report_dir}/pylint.report".format(
                pythonpath_prefix=pythonpath_prefix,
                flags=flags,
                apps=apps_list,
                report_dir=report_dir
            )
        )


@task('prereqs.install')
def pep8(system="lms,cms,common", **kwargs):
    """
    Run pep8 on system code
    """
    if system:
        systems = system.split(',')
    else:
        system = ['lms', 'cms']

    for system in systems:
        # Directory to put the pep8 report in.
        # This makes the folder if it doesn't already exist.
        report_dir = Env.REPORT_ROOT / system
        report_dir.makedirs_p()

        sh('pep8 {system} | tee {report_dir}/pep8.report'.format(system=system, report_dir=report_dir))


@task('prereqs.install')
def quality(**kwargs):
    """
    Build the html diff quality reports, and print the reports to the console.
    """

    # Directory to put the diff reports in.
    # This makes the folder if it doesn't already exist.
    dquality_dir = Env.REPORT_ROOT / "diff_quality"
    dquality_dir.makedirs_p()

    # Generage diff-quality html report for pep8, and print to console
    # If pep8 reports exist, use those
    # Otherwise, `diff-quality` will call pep8 itself

    pep8_files = []
    for subdir, _dirs, files in Env.REPORT_ROOT.walk():
        for f in files:
            if f == "pep8.report":
                pep8_files.append(subdir / f)

    pep8_reports = u' '.join(pep8_files)

    sh(
        "diff-quality --violations=pep8 --html-report {dquality_dir}/"
        "diff_quality_pep8.html {pep8_reports}".format(
            dquality_dir=dquality_dir, pep8_reports=pep8_reports)
    )

    sh(
        "diff-quality --violations=pep8 {pep8_reports}".format(
            pep8_reports=pep8_reports)
    )

    # Generage diff-quality html report for pylint, and print to console
    # If pylint reports exist, use those
    # Otherwise, `diff-quality` will call pylint itself

    pylint_files = []
    for subdir, _dirs, files in Env.REPORT_ROOT.walk():
        for f in files:
            if f == "pylint.report":
                pylint_files.append(subdir / f)

    pylint_reports = u' '.join(pylint_files)

    pythonpath_prefix = (
        "PYTHONPATH=$PYTHONPATH:lms:lms/djangoapps:lms/lib:cms:cms/djangoapps:cms/lib:"
        "common:common/djangoapps:common/lib"
    )

    sh(
        "{pythonpath_prefix} diff-quality --violations=pylint --html-report "
        "{dquality_dir}/diff_quality_pylint.html {pylint_reports}".format(
            pythonpath_prefix=pythonpath_prefix,
            dquality_dir=dquality_dir,
            pylint_reports=pylint_reports
        )
    )

    sh(
        "{pythonpath_prefix} diff-quality --violations=pylint {pylint_reports}".format(
            pythonpath_prefix=pythonpath_prefix,
            pylint_reports=pylint_reports
        )
    )


@task
def run_all():
    pylint()
    pep8()
    quality()

ns = Collection(pylint, pep8, quality)
ns.add_task(run_all, name="all", default=True)

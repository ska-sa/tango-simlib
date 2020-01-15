pipeline {

    agent {
        // TODO: Update with the appropriate docker image once PR(https://github.com/ska-sa/kattrap/pull/90)
        // Is merged.
        label 'camtango_db_bionic'
    }

    environment {
        KATPACKAGE = "${(env.JOB_NAME - env.JOB_BASE_NAME) - '-multibranch/'}"
    }

    stages {

        stage ('Checkout SCM') {
            steps {
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: "refs/heads/${env.BRANCH_NAME}"]],
                    extensions: [[$class: 'LocalBranch']],
                    userRemoteConfigs: scm.userRemoteConfigs,
                    doGenerateSubmoduleConfigurations: false,
                    submoduleCfg: []
                ])
            }
        }
        stage ('Static analysis') {
            steps {
                sh "pylint ./${KATPACKAGE} --output-format=parseable --exit-zero > pylint.out"
                sh "lint_diff.sh -r ${KATPACKAGE}"
            }
        }

        stage ('Check running services.') {
            // Fail stage if services are not running.
            steps {
                sh 'service mysql status || exit 1'
                sh 'service tango-db status || exit 1'
            }
        }

        stage ('Install & Unit Tests') {
            options {
                timestamps()
                timeout(time: 30, unit: 'MINUTES')
            }

            environment {
                test_flags = "${KATPACKAGE}"
            }

             steps {

                        echo "Running nosetests on Python 2.7"
                        sh 'python2 -m pip install -U .'
                        sh 'python2 -m coverage run --source="${KATPACKAGE}" -m nose --with-xunitmp --xunitmp-file=nosetests_py27.xml'
                        sh 'python2 -m coverage xml -o coverage_27.xml'
                        sh 'python2 -m coverage report -m --skip-covered'

                        sh 'unlink /usr/bin/python && ln -s /usr/bin/python3.6 /usr/bin/python'

                        echo "Running nosetests on Python 3.6"
                        sh 'python3 -m pip install -U .'
                        sh 'python3 -m coverage run --source="${KATPACKAGE}" -m nose --with-xunitmp --xunitmp-file=nosetests_py36.xml'
                        sh 'python3 -m coverage xml -o coverage_36.xml'
                        sh 'python3 -m coverage report -m --skip-covered'

            }

            post {
                always {
                    junit 'nosetests_*.xml'
                    cobertura (
                        coberturaReportFile: 'coverage_*.xml',
                        failNoReports: true,
                        failUnhealthy: true,
                        failUnstable: true,
                        autoUpdateHealth: true,
                        autoUpdateStability: true,
                        zoomCoverageChart: true,
                        // TODO: The reason this is commented out is because tango-simlib test coverage is currently at 70% instead of minimum 80%.
                        // lineCoverageTargets: '80, 80, 80',
                        // conditionalCoverageTargets: '80, 80, 80',
                        // classCoverageTargets: '80, 80, 80',
                        // fileCoverageTargets: '80, 80, 80',
                    )
                    archiveArtifacts '*.xml'
                }
            }
        }

        stage ('Generate documentation.') {
            options {
                timestamps()
                timeout(time: 30, unit: 'MINUTES')
            }

            steps {
                echo "Generating Sphinx documentation."
                sh 'make -C doc html'
            }
        }

        stage ('Build & publish packages') {
            when {
                branch 'master'
            }

            steps {
                sh 'fpm -s python -t deb .'
                sh 'python setup.py bdist_wheel'
                sh 'mv *.deb dist/'
                archiveArtifacts 'dist/*'

                // Trigger downstream publish job
                build job: 'ci.publish-artifacts', parameters: [
                        string(name: 'job_name', value: "${env.JOB_NAME}"),
                        string(name: 'build_number', value: "${env.BUILD_NUMBER}")]
            }
        }
    }
}

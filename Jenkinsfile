pipeline {

    agent {
        label 'camtango_db'
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
                //sh "lint_diff.sh -r ${KATPACKAGE}"
            }

            post {
                always {
                    recordIssues(tool: pyLint(pattern: 'pylint.out'))
                }
            }
        }

        stage ('Start Services') {
            steps {
                sh 'nohup service mysql start'
                sh 'nohup service tango-db start'
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

             parallel {
                stage ('py27') {
                    steps {
                        echo "Running nosetests on Python 2.7"
                        sh 'tox -e py27 -vv'
                    }
                }

                stage ('py36') {
                    steps {
                        echo "Not yet implemented."
                        // echo "Running nosetests on Python 3.6"
                        // sh 'tox -e py36 -vv'
                    }
                }
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
                        // lineCoverageTargets: '80, 80, 80',
                        // conditionalCoverageTargets: '80, 80, 80',
                        // classCoverageTargets: '80, 80, 80',
                        // fileCoverageTargets: '80, 80, 80',
                    )
                    archiveArtifacts '*.xml'
                }
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


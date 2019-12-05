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
        // TODO: This is commented out for efficient and quick response cycle should be uncommented once migration is done
        // stage ('Static analysis') {
        //     steps {
        //         sh "pylint ./${KATPACKAGE} --output-format=parseable --exit-zero > pylint.out"
        //         sh "lint_diff.sh -r ${KATPACKAGE}"
        //     }

        //     post {
        //         always {
        //             recordIssues(tool: pyLint(pattern: 'pylint.out'))
        //         }
        //     }
        // }

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
                        sh 'python2 -m pip install . -U'
                        sh 'python2 -m pip install nose_xunitmp'
                        sh "python2 setup.py nosetests --with-xunitmp --with-xcoverage --cover-package=${KATPACKAGE} --with-xunit --xunit-file=nosetests_py27.xml"
                    }
                }

                stage ('py36') {
                    steps {
                        //echo "Not yet implemented."
                         echo "Running nosetests on Python 3.6"
                         sh 'python3.6 -m pip install . -U --user'
                         sh 'python3.6 -m pip install nose_xunitmp --user'
                         sh "python3.6 setup.py nosetests --with-xunitmp --with-xcoverage --cover-package=${KATPACKAGE}"
                    }
                }
            }

            post {
                always {
                    junit 'nosetests.xml'
                    cobertura (
                        coberturaReportFile: 'coverage.xml',
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


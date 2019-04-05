pipeline {

    agent {
        label 'camtango_nodb'
    }

    stages {
        stage('Checkout SCM') {
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

        stage('Install & Unit Tests') {
            options {
                timestamps()
                timeout(time: 30, unit: 'MINUTES')
            }

            steps {
                sh 'nohup service mysql start'
                sh 'nohup service tango-db start'
                sh 'pip install nose_xunitmp --user'
                sh 'pip install . -U --pre --user'
                sh 'python setup.py test --with-xunitmp --xunitmp-file nosetests.xml'
            }

            post {
                always {
                    junit 'nosetests.xml'
                    archiveArtifacts 'nosetests.xml'
                }
            }
        }

        stage('Build .whl & .deb') {
            steps {
                sh 'fpm -s python -t deb .'
                sh 'python setup.py bdist_wheel'
                sh 'mv *.deb dist/'
            }
        }

        stage('Archive build artifact: .whl & .deb') {
            steps {
                archiveArtifacts 'dist/*'
            }
        }

        stage('Trigger downstream publish') {
            steps {
                build(job: 'publish-local', parameters: [
                    string(name: 'artifact_source', value: "${currentBuild.absoluteUrl}/artifact/dist/*zip*/dist.zip"),
                    string(name: 'source_branch', value: "${env.BRANCH_NAME}")])
            }
        }
    }
}

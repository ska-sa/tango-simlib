node('docker') {

    withDockerContainer(
        image: 'camtango_db:latest',
        args: '-u root'
    ) {
        
    stage 'Checkout SCM'
        checkout([
            $class: 'GitSCM',
            branches: [[name: "refs/heads/${env.BRANCH_NAME}"]],
            extensions: [[$class: 'LocalBranch']],
            userRemoteConfigs: scm.userRemoteConfigs,
            doGenerateSubmoduleConfigurations: false,
            submoduleCfg: []
        ])

    stage 'Install & Unit Tests'
        timestamps {
            timeout(time: 30, unit: 'MINUTES') {
                try {
                    sh 'nohup service mysql start'
                    sh 'nohup service tango-db start'
                    sh 'pip install . -U'
                    sh 'pip install nose_xunitmp'
                    sh 'python setup.py test --with-xunitmp --xunitmp-file nosetests.xml'
                } finally {
                    step([$class: 'JUnitResultArchiver', testResults: 'nosetests.xml'])
                }
            }
        }
    stage 'Build .whl & .deb'
        sh 'fpm -s python -t deb .'
        sh 'python setup.py bdist_wheel'
        sh 'mv *.deb dist/'

    stage 'Archive build artifact: .whl & .deb'
        archive 'dist/*'

    stage 'Trigger downstream publish'
        build job: 'publish-local', parameters: [
            string(name: 'artifact_source', value: "${currentBuild.absoluteUrl}/artifact/dist/*zip*/dist.zip"),
            string(name: 'source_branch', value: "${env.BRANCH_NAME}")]
    }

}

pipeline {
    /* agent any */
    agent {
        label "host088"
    }
    options {
        timestamps()
        timeout(time: 5, unit: 'MINUTES')
    }
    stages {
        stage('build') {
            steps {
                script {
                    echo "Start building..."
                    sh "chmod 777 ./make.sh"
                    sh "chmod 777 ./jenkins.sh"
                    sh "./make.sh"
                }
            }
        }
        stage('upload') {
            steps {
                script {
                    echo "Start uploading..."
                    sh "./jenkins.sh"
                }
            }
        }
    }
}

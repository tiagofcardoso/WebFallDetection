document.addEventListener('DOMContentLoaded', function () {
    const statusElement = document.getElementById('detection-status');
    const logContainer = document.getElementById('logContainer');
    const settingsForm = document.getElementById('settingsForm');

    // Função para adicionar log
    function addLogEntry(message, isAlert = false) {
        const entry = document.createElement('div');
        entry.className = `log-entry${isAlert ? ' alert' : ''}`;
        entry.textContent = `${new Date().toLocaleTimeString()} - ${message}`;
        logContainer.insertBefore(entry, logContainer.firstChild);

        // Limitar número de logs
        while (logContainer.children.length > 100) {
            logContainer.removeChild(logContainer.lastChild);
        }
    }

    // Atualizar status
    function updateStatus() {
        fetch('/status')
            .then(response => response.json())
            .then(data => {
                if (data.fall_detected) {
                    statusElement.textContent = 'QUEDA DETECTADA!';
                    statusElement.className = 'text-danger';
                    if (data.alert_sent) {
                        addLogEntry('Alerta enviado: Queda detectada!', true);
                    }
                } else {
                    statusElement.textContent = 'Monitorando';
                    statusElement.className = 'text-success';
                }
            })
            .catch(error => console.error('Error:', error));
    }

    // Salvar configurações
    document.getElementById('saveSettings').addEventListener('click', function () {
        const settings = {
            sensitivity: document.getElementById('sensitivityRange').value,
            immobilityTime: document.getElementById('immobilityTime').value,
            enableAlerts: document.getElementById('enableAlerts').checked
        };

        fetch('/update_settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(settings)
        })
            .then(response => response.json())
            .then(data => {
                addLogEntry('Configurações atualizadas');
                bootstrap.Modal.getInstance(document.getElementById('settingsModal')).hide();
            })
            .catch(error => console.error('Error:', error));
    });

    // Limpar logs
    document.getElementById('clearLogs').addEventListener('click', function () {
        logContainer.innerHTML = '';
        addLogEntry('Logs limpos');
    });

    // Atualizar status periodicamente
    setInterval(updateStatus, 1000);

    // Adicionar log inicial
    addLogEntry('Sistema iniciado');

    // Inicializar gráfico com opções responsivas
    const ctx = document.getElementById('detectionChart').getContext('2d');
    const detectionChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Detecções por hora',
                data: [],
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1,
                pointRadius: window.innerWidth < 768 ? 2 : 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'nearest',
                intersect: false
            },
            plugins: {
                legend: {
                    display: window.innerWidth >= 768
                },
                tooltip: {
                    enabled: true,
                    mode: 'index'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1,
                        font: {
                            size: window.innerWidth < 768 ? 10 : 12
                        }
                    }
                },
                x: {
                    ticks: {
                        maxRotation: window.innerWidth < 768 ? 45 : 0,
                        font: {
                            size: window.innerWidth < 768 ? 10 : 12
                        }
                    }
                }
            }
        }
    });

    // Adicionar listener para redimensionamento
    window.addEventListener('resize', () => {
        const isMobile = window.innerWidth < 768;

        // Atualizar opções do gráfico
        detectionChart.options.plugins.legend.display = !isMobile;
        detectionChart.options.scales.x.ticks.maxRotation = isMobile ? 45 : 0;
        detectionChart.options.scales.x.ticks.font.size = isMobile ? 10 : 12;
        detectionChart.options.scales.y.ticks.font.size = isMobile ? 10 : 12;
        detectionChart.data.datasets[0].pointRadius = isMobile ? 2 : 3;

        detectionChart.update();
    });

    // Contador de tempo de monitoramento
    let startTime = new Date();
    function updateMonitoringTime() {
        const now = new Date();
        const diff = now - startTime;
        const hours = Math.floor(diff / 3600000);
        const minutes = Math.floor((diff % 3600000) / 60000);
        const seconds = Math.floor((diff % 60000) / 1000);
        document.getElementById('monitoringTime').textContent =
            `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }

    // Atualizar estatísticas
    function updateStats() {
        fetch('/system_stats')
            .then(response => response.json())
            .then(data => {
                // Atualizar CPU e FPS
                document.getElementById('cpuUsage').style.width = `${data.cpu_usage}%`;
                document.getElementById('cpuUsage').textContent = `${data.cpu_usage}%`;
                document.getElementById('currentFps').textContent = `${data.fps} FPS`;

                // Atualizar gráfico
                if (data.detections_per_hour.length > 0) {
                    detectionChart.data.labels = data.detections_per_hour.map(d => d.hour);
                    detectionChart.data.datasets[0].data = data.detections_per_hour.map(d => d.count);
                    detectionChart.update();
                }

                // Atualizar contadores
                document.getElementById('todayDetections').textContent = data.total_detections;
            })
            .catch(error => console.error('Error:', error));
    }

    // Atualizar tempos
    setInterval(updateMonitoringTime, 1000);
    setInterval(updateStats, 5000);
});

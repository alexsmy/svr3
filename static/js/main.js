document.addEventListener('DOMContentLoaded', () => {
    const getInfoBtn = document.getElementById('get_info_btn');
    const loadingIndicator = document.getElementById('loading_indicator');
    const serverInfoOutput = document.getElementById('server_info_output');

    getInfoBtn.addEventListener('click', fetchServerInfo);

    async function fetchServerInfo() {
        getInfoBtn.disabled = true;
        loadingIndicator.style.display = 'block';
        serverInfoOutput.innerHTML = ''; // Очищаем предыдущие результаты

        try {
            const response = await fetch('/get_server_info');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            displayServerInfo(data);
        } catch (error) {
            console.error("Ошибка при получении информации о сервере:", error);
            serverInfoOutput.innerHTML = `<div class="info-item"><span class="label">Ошибка</span><span class="value">Не удалось загрузить информацию о сервере: ${error.message}</span></div>`;
        } finally {
            getInfoBtn.disabled = false;
            loadingIndicator.style.display = 'none';
        }
    }

    function displayServerInfo(data) {
        let html = '';

        // Местоположение сервера
        if (data.location) {
            html += `
                <div class="info-item">
                    <span class="label">📍 Местоположение сервера</span>
                    <span class="value">${data.location.city}, ${data.location.country} <small>(${data.location.ip})</small></span>
                </div>
            `;
        }

        // Информация об ОС
        if (data.os) {
            html += `
                <div class="info-item">
                    <span class="label">🖥️ Операционная система</span>
                    <span class="value">${data.os.system} ${data.os.release} (${data.os.version})</span>
                    <ul>
                        <li><strong>Имя узла:</strong> ${data.os.node_name}</li>
                        <li><strong>Архитектура:</strong> ${data.os.machine} (${data.os.processor_arch})</li>
                        <li><strong>Время работы (Uptime):</strong> ${data.os.uptime}</li>
                        <li><strong>Время загрузки:</strong> ${data.os.boot_time}</li>
                        <li><strong>Виртуализация:</strong> ${data.os.virtualization}</li>
                    </ul>
                </div>
            `;
        }

        // Информация о CPU
        if (data.cpu) {
            html += `
                <div class="info-item">
                    <span class="label">🧠 Процессор (CPU)</span>
                    <span class="value">${data.cpu.model_name || 'Неизвестно'}</span>
                    <ul>
                        <li><strong>Ядер:</strong> ${data.cpu.logical_cores} (физ. ${data.cpu.physical_cores})</li>
                        <li><strong>Текущая частота:</strong> ${data.cpu.current_frequency_mhz} МГц</li>
                        <li><strong>Мин. частота:</strong> ${data.cpu.min_frequency_mhz} МГц</li>
                        <li><strong>Макс. частота:</strong> ${data.cpu.max_frequency_mhz} МГц</li>
                        <li><strong>Использование:</strong> ${data.cpu.usage_percent}%</li>
                        <li><strong>Средняя нагрузка (1/5/15 мин):</strong> ${data.cpu.load_average_1_min} / ${data.cpu.load_average_5_min} / ${data.cpu.load_average_15_min}</li>
                    </ul>
                </div>
            `;
        }

        // Информация о RAM
        if (data.memory) {
            html += `
                <div class="info-item">
                    <span class="label">💾 Оперативная память (RAM)</span>
                    <span class="value">Всего: ${data.memory.total_gb} ГБ (Использовано: ${data.memory.percent_used}%)</span>
                    <ul>
                        <li><strong>Доступно:</strong> ${data.memory.available_gb} ГБ</li>
                        <li><strong>Использовано:</strong> ${data.memory.used_gb} ГБ</li>
                        <li><strong>Swap:</strong> ${data.memory.swap_total_gb} ГБ (Использовано: ${data.memory.swap_percent_used}%)</li>
                    </ul>
                </div>
            `;
        }

        // Информация о дисковых разделах
        if (data.disk_partitions && data.disk_partitions.length > 0) {
            let partitionHtml = '';
            data.disk_partitions.forEach(partition => {
                if (partition.error) {
                    partitionHtml += `<li><strong>${partition.mountpoint} (${partition.device}):</strong> ${partition.error}</li>`;
                } else {
                    partitionHtml += `<li><strong>${partition.mountpoint} (${partition.device}, ${partition.fstype}):</strong> ${partition.used_gb} ГБ из ${partition.total_gb} ГБ (${partition.percent_used}%)</li>`;
                }
            });
            html += `
                <div class="info-item">
                    <span class="label">💽 Дисковые разделы</span>
                    <ul>
                        ${partitionHtml}
                    </ul>
                </div>
            `;
        }

        // Информация о дисковом I/O
        if (data.disk_io) {
            if (data.disk_io.error) {
                html += `
                    <div class="info-item">
                        <span class="label">📊 Дисковый I/O</span>
                        <span class="value">${data.disk_io.error}</span>
                    </div>
                `;
            } else {
                html += `
                    <div class="info-item">
                        <span class="label">📊 Дисковый I/O</span>
                        <span class="value">Чтение: ${data.disk_io.read_bytes_gb} ГБ / Запись: ${data.disk_io.write_bytes_gb} ГБ</span>
                        <ul>
                            <li><strong>Операций чтения:</strong> ${data.disk_io.read_count}</li>
                            <li><strong>Операций записи:</strong> ${data.disk_io.write_count}</li>
                        </ul>
                    </div>
                `;
            }
        }

        // Информация о Python
        if (data.python) {
            html += `
                <div class="info-item">
                    <span class="label">🐍 Среда Python</span>
                    <span class="value">${data.python.version}</span>
                    <ul>
                        <li><strong>Исполняемый файл:</strong> ${data.python.executable}</li>
                        <li><strong>Платформа:</strong> ${data.python.platform}</li>
                    </ul>
                </div>
            `;
        }

        // Сетевые интерфейсы
        if (data.network_interfaces && Object.keys(data.network_interfaces).length > 0) {
            let interfaceList = '';
            for (const [name, ips] of Object.entries(data.network_interfaces)) {
                interfaceList += `<li><strong>${name}:</strong> ${ips.join(', ')}</li>`;
            }
            html += `
                <div class="info-item">
                    <span class="label">🌐 Сетевые интерфейсы</span>
                    <ul>
                        ${interfaceList}
                    </ul>
                </div>
            `;
        }

        // Сетевой I/O
        if (data.network_io) {
            if (data.network_io.error) {
                html += `
                    <div class="info-item">
                        <span class="label">📈 Сетевой I/O</span>
                        <span class="value">${data.network_io.error}</span>
                    </div>
                `;
            } else {
                html += `
                    <div class="info-item">
                        <span class="label">📈 Сетевой I/O</span>
                        <span class="value">Отправлено: ${data.network_io.bytes_sent_gb} ГБ / Получено: ${data.network_io.bytes_recv_gb} ГБ</span>
                        <ul>
                            <li><strong>Отправлено пакетов:</strong> ${data.network_io.packets_sent}</li>
                            <li><strong>Получено пакетов:</strong> ${data.network_io.packets_recv}</li>
                            <li><strong>Ошибок входящих:</strong> ${data.network_io.errin}</li>
                            <li><strong>Ошибок исходящих:</strong> ${data.network_io.errout}</li>
                            <li><strong>Потеряно входящих:</strong> ${data.network_io.dropin}</li>
                            <li><strong>Потеряно исходящих:</strong> ${data.network_io.dropout}</li>
                        </ul>
                    </div>
                `;
            }
        }

        serverInfoOutput.innerHTML = html;
    }
});

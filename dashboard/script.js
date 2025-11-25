// API Base URL
const API_BASE = 'http://localhost:5001/api';

// Charts
let wealthChart = null;
let levelsChart = null;

// Filter state
let allTransactions = [];
let allLeaderboards = {
    topRich: [],
    topLevels: [],
    topPvP: []
};

// Wait for DOM to load
document.addEventListener('DOMContentLoaded', () => {
    // Theme management
    const themeToggle = document.getElementById('themeToggle');
    const savedTheme = localStorage.getItem('dashboard-theme') || 'dark';

    // Apply saved theme
    if (savedTheme === 'light') {
        document.body.classList.add('light-theme');
        themeToggle.querySelector('.icon').textContent = '☀️';
    }

    // Theme toggle event
    themeToggle.addEventListener('click', () => {
        document.body.classList.toggle('light-theme');
        const isLight = document.body.classList.contains('light-theme');
        themeToggle.querySelector('.icon').textContent = isLight ? '☀️' : '🌙';
        localStorage.setItem('dashboard-theme', isLight ? 'light' : 'dark');
    });

    // Utility Functions
    function formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(2) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toLocaleString('ru-RU');
    }

    function formatDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 1) return 'только что';
        if (minutes < 60) return `${minutes} мин назад`;
        if (hours < 24) return `${hours} ч назад`;
        if (days < 7) return `${days} д назад`;

        return date.toLocaleDateString('ru-RU');
    }

    function getUserName(userId) {
        // В реальном приложении можно было бы кешировать имена пользователей
        return `User ${userId.slice(0, 8)}...`;
    }

    function getTransactionIcon(type) {
        const icons = {
            'daily': '📅',
            'weekly': '📆',
            'monthly': '🗓️',
            'work': '💼',
            'game': '🎮',
            'bank': '🏦',
            'business': '🏢',
            'social': '🤝',
            'tournament': '🏆',
            'level_up': '⭐',
            'crime': '🔫',
            'pvp': '⚔️'
        };
        return icons[type] || '💰';
    }

    // Update last update time
    function updateLastUpdateTime() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('ru-RU');
        document.getElementById('lastUpdate').textContent = timeString;
    }

    // Fetch and update stats
    async function updateStats() {
        try {
            const response = await fetch(`${API_BASE}/stats`);
            const data = await response.json();

            // Update overview stats
            const overview = data.overview;
            document.getElementById('totalUsers').textContent = formatNumber(overview.total_users);
            document.getElementById('totalBalance').textContent = formatNumber(overview.total_balance);
            document.getElementById('totalBank').textContent = formatNumber(overview.total_bank_balance);
            document.getElementById('totalBusinesses').textContent = formatNumber(overview.total_businesses);
            document.getElementById('totalGames').textContent = formatNumber(overview.total_games_played);
            document.getElementById('totalDuels').textContent = formatNumber(overview.total_duels);

            // Update leaderboards
            updateLeaderboard('topRich', data.leaderboards.top_rich, 'balance');
            updateLeaderboard('topLevels', data.leaderboards.top_levels, 'level');
            updatePvPLeaderboard(data.leaderboards.top_pvp);

            updateLastUpdateTime();
        } catch (error) {
            console.error('Error fetching stats:', error);
        }
    }

    // Update leaderboard
    function updateLeaderboard(elementId, data, valueKey) {
        const container = document.getElementById(elementId);

        if (!data || data.length === 0) {
            container.innerHTML = '<div class="loading">Нет данных</div>';
            return;
        }

        // Store original data
        if (elementId === 'topRich') allLeaderboards.topRich = data;
        if (elementId === 'topLevels') allLeaderboards.topLevels = data;

        renderLeaderboard(container, data, valueKey);
    }

    function renderLeaderboard(container, data, valueKey) {
        container.innerHTML = data.map((item, index) => {
            const rank = index + 1;
            let rankClass = '';
            if (rank === 1) rankClass = 'gold';
            else if (rank === 2) rankClass = 'silver';
            else if (rank === 3) rankClass = 'bronze';

            const value = item.value || item.data[valueKey];
            const userName = getUserName(item.user_id);

            let detailText = '';
            if (valueKey === 'balance') {
                detailText = `${formatNumber(value)} 💎`;
            } else if (valueKey === 'level') {
                const xp = item.data.xp || 0;
                detailText = `${formatNumber(xp)} XP`;
            }

            return `
            <div class="leaderboard-item" data-user-id="${item.user_id}">
                <div class="leaderboard-rank ${rankClass}">#${rank}</div>
                <div class="leaderboard-info">
                    <div class="leaderboard-name">${userName}</div>
                    <div class="leaderboard-detail">${detailText}</div>
                </div>
                <div class="leaderboard-value">${valueKey === 'level' ? 'Ур. ' : ''}${formatNumber(value)}</div>
            </div>
        `;
        }).join('');
    }

    // Leaderboard search
    const leaderboardSearch = document.getElementById('leaderboardSearch');
    leaderboardSearch.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();

        if (!query) {
            // Show all
            renderLeaderboard(document.getElementById('topRich'), allLeaderboards.topRich, 'balance');
            renderLeaderboard(document.getElementById('topLevels'), allLeaderboards.topLevels, 'level');
            if (allLeaderboards.topPvP.length > 0) {
                updatePvPLeaderboard(allLeaderboards.topPvP);
            }
            return;
        }

        // Filter by user ID
        const filteredRich = allLeaderboards.topRich.filter(item =>
            item.user_id.toLowerCase().includes(query)
        );
        const filteredLevels = allLeaderboards.topLevels.filter(item =>
            item.user_id.toLowerCase().includes(query)
        );
        const filteredPvP = allLeaderboards.topPvP.filter(item =>
            item.user_id.toLowerCase().includes(query)
        );

        renderLeaderboard(document.getElementById('topRich'), filteredRich, 'balance');
        renderLeaderboard(document.getElementById('topLevels'), filteredLevels, 'level');
        if (filteredPvP.length > 0) {
            updatePvPLeaderboard(filteredPvP);
        } else {
            document.getElementById('topPvP').innerHTML = '<div class="loading">Нет результатов</div>';
        }
    });

    // Update PvP leaderboard
    function updatePvPLeaderboard(data) {
        const container = document.getElementById('topPvP');

        if (!data || data.length === 0) {
            container.innerHTML = '<div class="loading">Нет данных</div>';
            return;
        }

        // Store original data
        allLeaderboards.topPvP = data;

        container.innerHTML = data.map((item, index) => {
            const rank = index + 1;
            let rankClass = '';
            if (rank === 1) rankClass = 'gold';
            else if (rank === 2) rankClass = 'silver';
            else if (rank === 3) rankClass = 'bronze';

            const userName = getUserName(item.user_id);
            const winRate = item.wins + item.losses > 0
                ? ((item.wins / (item.wins + item.losses)) * 100).toFixed(1)
                : 0;

            return `
            <div class="leaderboard-item">
                <div class="leaderboard-rank ${rankClass}">#${rank}</div>
                <div class="leaderboard-info">
                    <div class="leaderboard-name">${userName}</div>
                    <div class="leaderboard-detail">${item.rank} • ${winRate}% побед</div>
                </div>
                <div class="leaderboard-value">${item.wins}W/${item.losses}L</div>
            </div>
        `;
        }).join('');
    }

    // Update transactions
    async function updateTransactions() {
        try {
            const response = await fetch(`${API_BASE}/transactions`);
            const data = await response.json();

            // Store all transactions
            allTransactions = data || [];

            // Apply current filters
            applyTransactionFilters();
        } catch (error) {
            console.error('Error fetching transactions:', error);
        }
    }

    function applyTransactionFilters() {
        const searchQuery = document.getElementById('transactionSearch').value.toLowerCase().trim();
        const typeFilter = document.getElementById('transactionTypeFilter').value;

        let filtered = allTransactions;

        // Filter by type
        if (typeFilter !== 'all') {
            filtered = filtered.filter(trans => trans.type === typeFilter);
        }

        // Filter by search query (user ID or details)
        if (searchQuery) {
            filtered = filtered.filter(trans =>
                trans.user_id.toLowerCase().includes(searchQuery) ||
                trans.details.toLowerCase().includes(searchQuery)
            );
        }

        renderTransactions(filtered);
    }

    function renderTransactions(data) {
        const container = document.getElementById('transactionsList');

        if (!data || data.length === 0) {
            container.innerHTML = '<div class="loading">Нет транзакций</div>';
            return;
        }

        container.innerHTML = data.slice(0, 50).map(trans => {
            const icon = getTransactionIcon(trans.type);
            const amount = trans.amount;
            const amountClass = amount >= 0 ? 'positive' : 'negative';
            const amountSign = amount >= 0 ? '+' : '';
            const userName = getUserName(trans.user_id);
            const time = formatDate(trans.timestamp);

            return `
            <div class="transaction-item" data-type="${trans.type}" data-user-id="${trans.user_id}">
                <div class="transaction-info">
                    <div class="transaction-type">${icon} ${trans.details}</div>
                    <div class="transaction-details">${userName} • ${time}</div>
                </div>
                <div class="transaction-amount ${amountClass}">
                    ${amountSign}${formatNumber(Math.abs(amount))} 💎
                </div>
            </div>
        `;
        }).join('');
    }

    // Update charts
    async function updateCharts() {
        try {
            const [economyRes, levelsRes] = await Promise.all([
                fetch(`${API_BASE}/economy`),
                fetch(`${API_BASE}/levels`)
            ]);

            const economy = await economyRes.json();
            const levels = await levelsRes.json();

            // Wealth distribution chart
            updateWealthChart(economy);

            // Levels distribution chart
            updateLevelsChart(levels);
        } catch (error) {
            console.error('Error updating charts:', error);
        }
    }

    function updateWealthChart(economy) {
        const balances = Object.values(economy).map(u => u.balance || 0);

        // Create distribution buckets
        const buckets = {
            '0-10K': 0,
            '10K-100K': 0,
            '100K-1M': 0,
            '1M-10M': 0,
            '10M+': 0
        };

        balances.forEach(balance => {
            if (balance < 10000) buckets['0-10K']++;
            else if (balance < 100000) buckets['10K-100K']++;
            else if (balance < 1000000) buckets['100K-1M']++;
            else if (balance < 10000000) buckets['1M-10M']++;
            else buckets['10M+']++;
        });

        const ctx = document.getElementById('wealthChart');

        if (wealthChart) {
            wealthChart.destroy();
        }

        wealthChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: Object.keys(buckets),
                datasets: [{
                    data: Object.values(buckets),
                    backgroundColor: [
                        'rgba(52, 152, 219, 0.8)',
                        'rgba(93, 173, 226, 0.8)',
                        'rgba(46, 204, 113, 0.8)',
                        'rgba(243, 156, 18, 0.8)',
                        'rgba(155, 89, 182, 0.8)'
                    ],
                    borderColor: 'rgba(26, 31, 46, 0.8)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#b0b8c4',
                            font: { size: 12 }
                        }
                    }
                }
            }
        });
    }

    function updateLevelsChart(levels) {
        const levelValues = Object.values(levels).map(u => u.level || 0);

        // Create distribution buckets
        const buckets = {
            '1-10': 0,
            '11-25': 0,
            '26-50': 0,
            '51-75': 0,
            '76-100': 0
        };

        levelValues.forEach(level => {
            if (level <= 10) buckets['1-10']++;
            else if (level <= 25) buckets['11-25']++;
            else if (level <= 50) buckets['26-50']++;
            else if (level <= 75) buckets['51-75']++;
            else buckets['76-100']++;
        });

        const ctx = document.getElementById('levelsChart');

        if (levelsChart) {
            levelsChart.destroy();
        }

        levelsChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: Object.keys(buckets),
                datasets: [{
                    label: 'Пользователей',
                    data: Object.values(buckets),
                    backgroundColor: 'rgba(52, 152, 219, 0.8)',
                    borderColor: 'rgba(52, 152, 219, 1)',
                    borderWidth: 2,
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: '#b0b8c4',
                            stepSize: 1
                        },
                        grid: {
                            color: 'rgba(52, 152, 219, 0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#b0b8c4'
                        },
                        grid: {
                            display: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    // Refresh all data
    async function refreshAll() {
        const btn = document.getElementById('refreshBtn');
        btn.disabled = true;
        btn.style.opacity = '0.6';

        await Promise.all([
            updateStats(),
            updateTransactions(),
            updateCharts()
        ]);

        btn.disabled = false;
        btn.style.opacity = '1';
    }

    // Transaction filter events
    document.getElementById('transactionSearch').addEventListener('input', applyTransactionFilters);
    document.getElementById('transactionTypeFilter').addEventListener('change', applyTransactionFilters);

    // Event listeners
    document.getElementById('refreshBtn').addEventListener('click', refreshAll);

    // Initial load
    refreshAll();

    // Auto-refresh every 30 seconds
    setInterval(refreshAll, 30000);

}); // End of DOMContentLoaded

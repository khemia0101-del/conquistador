/**
 * Conquistador Contractor Dashboard — Alpine.js
 */
function dashboard() {
    return {
        token: localStorage.getItem('conquistador_token') || '',
        email: '',
        password: '',
        loginError: '',
        leads: [],
        metrics: {},

        init() {
            if (this.token) {
                this.loadData();
            }
        },

        async login() {
            this.loginError = '';
            try {
                const res = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: this.email, password: this.password })
                });
                const data = await res.json();
                if (res.ok) {
                    this.token = data.access_token;
                    localStorage.setItem('conquistador_token', this.token);
                    this.loadData();
                } else {
                    this.loginError = data.detail || 'Invalid credentials.';
                }
            } catch (e) {
                this.loginError = 'Network error. Please try again.';
            }
        },

        logout() {
            this.token = '';
            localStorage.removeItem('conquistador_token');
            this.leads = [];
            this.metrics = {};
        },

        headers() {
            return {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.token}`
            };
        },

        async loadData() {
            await Promise.all([this.loadLeads(), this.loadMetrics()]);
        },

        async loadLeads() {
            try {
                const res = await fetch('/api/contractor/leads', { headers: this.headers() });
                if (res.ok) {
                    this.leads = await res.json();
                } else if (res.status === 401) {
                    this.logout();
                }
            } catch (e) {
                console.error('Failed to load leads:', e);
            }
        },

        async loadMetrics() {
            try {
                const res = await fetch('/api/contractor/metrics', { headers: this.headers() });
                if (res.ok) {
                    this.metrics = await res.json();
                }
            } catch (e) {
                console.error('Failed to load metrics:', e);
            }
        },

        async respond(leadId, action) {
            try {
                const res = await fetch(`/api/contractor/leads/${leadId}/${action}`, {
                    method: 'POST',
                    headers: this.headers()
                });
                if (res.ok) {
                    await this.loadData();
                }
            } catch (e) {
                console.error(`Failed to ${action} lead:`, e);
            }
        }
    };
}

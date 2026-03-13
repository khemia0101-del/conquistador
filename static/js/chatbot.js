/**
 * Conquistador Chatbot Widget — Alpine.js + WebSocket
 */
function chatbot() {
    return {
        isOpen: false,
        messages: [],
        input: '',
        typing: false,
        ws: null,

        toggle() {
            this.isOpen = !this.isOpen;
            if (this.isOpen && !this.ws) {
                this.connect();
            }
        },

        connect() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const url = `${protocol}//${window.location.host}/ws/chat`;

            try {
                this.ws = new WebSocket(url);

                this.ws.onopen = () => {
                    // Send initial greeting trigger
                    if (this.messages.length === 0) {
                        this.ws.send('hi');
                        this.typing = true;
                    }
                };

                this.ws.onmessage = (event) => {
                    this.typing = false;
                    this.messages.push({ role: 'assistant', content: event.data });
                    this.$nextTick(() => this.scrollToBottom());
                };

                this.ws.onclose = () => {
                    this.ws = null;
                };

                this.ws.onerror = () => {
                    this.typing = false;
                    this.messages.push({
                        role: 'assistant',
                        content: 'Connection issue. Please call us at (717) 397-9800.'
                    });
                };
            } catch (e) {
                this.messages.push({
                    role: 'assistant',
                    content: 'Chat is temporarily unavailable. Please call (717) 397-9800.'
                });
            }
        },

        send() {
            const msg = this.input.trim();
            if (!msg || !this.ws || this.ws.readyState !== WebSocket.OPEN) return;

            this.messages.push({ role: 'user', content: msg });
            this.ws.send(msg);
            this.input = '';
            this.typing = true;
            this.$nextTick(() => this.scrollToBottom());
        },

        scrollToBottom() {
            const container = this.$refs.messages;
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
        }
    };
}

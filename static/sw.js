self.addEventListener('push', function(event) {
    let data = {};
    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            data = { title: "Atenção", body: event.data.text() };
        }
    }

    const options = {
        body: data.body,
        icon: '/static/img/logo.png',
        badge: '/static/img/badge.png',
        vibrate: [200, 100, 200],                // Vibração dupla
        tag: 'vencimento-hoje',                  // Evita empilhar várias notificações iguais
        renotify: true,
        silent: false,            // Garante que não está em modo silencioso
        data: { url: data.url }     
    };
    event.waitUntil(
        self.registration.showNotification(data.title || "Descomplica MyFinance", options)
    );
});

// Abre o site ao clicar na notificação
self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    let targetUrl = event.notification.data.url || '/';

    // Se a URL não começar com http, nós adicionamos a origem do site
    if (!targetUrl.startsWith('http')) {
        targetUrl = new URL(targetUrl, self.location.origin).href;
    }
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(windowClients) {
            // Verifica se o site já está aberto em alguma aba
            for (let client of windowClients) {
                if (client.url === targetUrl && 'focus' in client) {
                    return client.focus();
                }
            }
            // Se não estiver aberto, abre uma nova aba com a URL correta
            if (clients.openWindow) {
                return clients.openWindow(targetUrl);
            }
        })
    );
});
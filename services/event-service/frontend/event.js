const API_URL = 'http://localhost';
const token = localStorage.getItem('access_token');

if (!token) {
    window.location.href = 'http://localhost/user/login.html';
}

function escapeHtml(text) {
    if (!text) return text;
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showLoader(show) {
    const loader = document.getElementById('loader');
    if (loader) loader.style.display = show ? 'block' : 'none';
}

function showMessage(text, type) {
    const msg = document.getElementById('message');
    if (!msg) return;
    msg.textContent = text;
    msg.className = `message ${type} show`;
    setTimeout(() => msg.classList.remove('show'), 3000);
}

function showModalMessage(elementId, text, type) {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = text;
        el.className = `message ${type} show`;
    }
}

function getStatusText(status) {
    const map = {
        'created': 'Создано',
        'active': 'Активно',
        'completed': 'Завершено',
        'archived': 'Архив'
    };
    return map[status] || status;
}

function goToProfile() {
    window.location.href = 'http://localhost/user/profile.html';
}

function goToWishlists() {
    window.location.href = 'http://localhost/wishlist/wishlist.html';
}

function goToEvents() {
    window.location.href = 'http://localhost/event/events.html';
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}

if (document.getElementById('eventsContainer')) {
    console.log('✅ Страница events.html загружена');

    let currentFilter = 'all';

    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentFilter = tab.dataset.filter;
            loadEvents(currentFilter);
        });
    });

    const createBtn = document.getElementById('createEventBtn');
    if (createBtn) {
        createBtn.addEventListener('click', () => {
            console.log('Кнопка создания нажата');
            window.location.href = 'event-form.html';
        });
    }

    loadEvents();

    async function loadEvents(filter = 'all') {
        showLoader(true);
        try {
            let url = `${API_URL}/api/event/events`;
            if (filter !== 'all') {
                url += `?status_filter=${filter}`;
            }

            const response = await fetch(url, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.status === 401) {
                localStorage.removeItem('access_token');
                window.location.href = 'http://localhost/user/login.html';
                return;
            }

            const events = await response.json();
            displayEvents(events);
        } catch (error) {
            showMessage('Ошибка загрузки мероприятий', 'error');
        } finally {
            showLoader(false);
        }
    }

    function displayEvents(events) {
        const container = document.getElementById('eventsContainer');
        if (!events || events.length === 0) {
            container.innerHTML = '<div class="empty-state"><i class="fas fa-calendar-times"></i><h3>Нет мероприятий</h3><p>Попробуйте изменить фильтр или создайте новое мероприятие.</p></div>';
            return;
        }

        let html = '';
        events.forEach(event => {
            const statusClass = `status-${event.status}`;
            const statusText = getStatusText(event.status);
            const startDate = new Date(event.start_date).toLocaleDateString();
            const endDate = new Date(event.end_date).toLocaleDateString();
            const deadline = new Date(event.registration_deadline).toLocaleDateString();
            const participants = event.participants_count || 0;

            html += `
                <div class="event-card" onclick="viewEvent(${event.id})">
                    <span class="event-status ${statusClass}">${statusText}</span>
                    <div class="event-name">${escapeHtml(event.name)}</div>
                    <div class="event-description">${escapeHtml(event.description || 'Нет описания')}</div>
                    <div class="event-dates">
                        <span><i class="fas fa-calendar-alt"></i> ${startDate} - ${endDate}</span>
                        <span><i class="fas fa-clock"></i> Регистрация до: ${deadline}</span>
                    </div>
                    <div class="event-meta">
                        <span class="participants-count"><i class="fas fa-users"></i> ${participants} уч.</span>
                        ${event.min_gift_amount || event.max_gift_amount ?
                    `<span class="gift-amount">💰 ${event.min_gift_amount || 0} - ${event.max_gift_amount || '∞'} ₽</span>` : ''}
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;
    }

    window.viewEvent = function (id) {
        window.location.href = `event-detail.html?id=${id}`;
    };
}

if (document.getElementById('eventContent')) {
    const urlParams = new URLSearchParams(window.location.search);
    const eventId = urlParams.get('id');
    if (!eventId) window.location.href = 'events.html';

    let currentEvent = null;

    loadEventDetail();

    async function loadEventDetail() {
        showLoader(true);
        try {
            const response = await fetch(`${API_URL}/api/event/events/${eventId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!response.ok) {
                if (response.status === 404) {
                    showMessage('Мероприятие не найдено', 'error');
                    setTimeout(() => window.location.href = 'events.html', 2000);
                    return;
                }
                throw new Error('Ошибка загрузки');
            }

            const event = await response.json();
            currentEvent = event;

            const partsResp = await fetch(`${API_URL}/api/event/events/${eventId}/participants-with-names`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const participants = partsResp.ok ? await partsResp.json() : [];

            const statusResp = await fetch(`${API_URL}/api/event/events/${eventId}/status`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const status = statusResp.ok ? await statusResp.json() : {};

            displayEventDetail(event, participants, status);

        } catch (error) {
            showMessage('Ошибка загрузки', 'error');
        } finally {
            showLoader(false);
        }
    }

    function displayEventDetail(event, participants, status) {
        document.getElementById('eventName').textContent = event.name;
        document.getElementById('eventDescription').textContent = event.description || 'Нет описания';

        const statusClass = `status-${event.status}`;
        document.getElementById('eventStatusBadge').textContent = getStatusText(event.status);
        document.getElementById('eventStatusBadge').className = `event-status ${statusClass}`;

        const start = new Date(event.start_date).toLocaleString();
        const end = new Date(event.end_date).toLocaleString();
        document.getElementById('eventDates').innerHTML = `${start} — ${end}`;

        const deadline = new Date(event.registration_deadline).toLocaleString();
        document.getElementById('eventDeadline').textContent = deadline;

        const amount = event.min_gift_amount || event.max_gift_amount
            ? `${event.min_gift_amount || 0} - ${event.max_gift_amount || '∞'} ₽`
            : 'Не указано';
        document.getElementById('eventAmount').textContent = amount;

        document.getElementById('eventParticipantsCount').textContent = participants.length;
        document.getElementById('eventOrganizer').textContent = `ID: ${event.organizer_id}`;

        const tbody = document.getElementById('participantsBody');
        if (tbody) {
            tbody.innerHTML = '';
            participants.forEach(p => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${escapeHtml(p.name)}</td>
                    <td>${p.selected_wishlist_id ? `Вишлист #${p.selected_wishlist_id}` : 'Не выбран'}</td>
                    <td>${p.gift_sent ? '✅' : '❌'}</td>
                    <td>${p.gift_sent_confirmation ? '✅' : '⏳'}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        const isOrganizer = (event.organizer_id == localStorage.getItem('user_id'));

        if (isOrganizer) {
            document.getElementById('organizerSection').style.display = 'block';
            const actionsDiv = document.getElementById('organizerActions');
            actionsDiv.innerHTML = '';

            if (status.can_start) {
                actionsDiv.innerHTML += `<button class="btn btn-success" onclick="startEvent()"><i class="fas fa-play"></i> Начать мероприятие</button>`;
            }
            if (status.can_draw) {
                actionsDiv.innerHTML += `<button class="btn btn-warning" onclick="drawAssignments()"><i class="fas fa-random"></i> Провести жеребьевку</button>`;
            }
            if (status.can_complete) {
                actionsDiv.innerHTML += `<button class="btn btn-info" onclick="completeEvent()"><i class="fas fa-check"></i> Завершить мероприятие</button>`;
            }
            actionsDiv.innerHTML += `<button class="btn btn-secondary" onclick="editEvent()"><i class="fas fa-edit"></i> Редактировать</button>`;
            actionsDiv.innerHTML += `<button class="btn btn-primary" onclick="showAddParticipantModal()"><i class="fas fa-user-plus"></i> Добавить пользователя</button>`;
        }

        const isParticipant = participants.some(p => p.user_id == localStorage.getItem('user_id'));
        if (isParticipant) {
            document.getElementById('participantSection').style.display = 'block';

            const partInfo = document.getElementById('participantInfo');
            const partActions = document.getElementById('participantActions');
            const myParticipant = participants.find(p => p.user_id == localStorage.getItem('user_id'));

            if (partInfo) {
                partInfo.innerHTML = `Статус: активен. ${myParticipant.gift_sent ? 'Подарок отправлен' : 'Подарок еще не отправлен'}.`;

                if (myParticipant.selected_wishlist_id) {
                    partInfo.innerHTML += `<br><br><span class="info-label">Выбранный вишлист:</span> ID ${myParticipant.selected_wishlist_id}`;
                }
            }

            if (partActions) {
                partActions.innerHTML = '';

                if (!event.draw_completed) {
                    partActions.innerHTML += `<button class="btn btn-primary" onclick="showSelectWishlistModal()">
                        <i class="fas fa-list"></i> ${myParticipant.selected_wishlist_id ? 'Изменить вишлист' : 'Выбрать вишлист'}
                    </button>`;
                }

                if (event.status === 'active' && !myParticipant.gift_sent) {
                    partActions.innerHTML += `<button class="btn btn-success" onclick="markGiftSent()"><i class="fas fa-gift"></i> Отметить, что подарок отправлен</button>`;
                }

                if (event.status === 'active' && myParticipant.gift_sent) {
                    checkIfUserIsRecipientAndUpdateUI(partActions, myParticipant);
                }
            }
        }

        if (event.draw_completed) {
            document.getElementById('drawSection').style.display = 'block';
            loadDrawInfo();
            loadRecipientWishlist();
        }

        document.getElementById('eventContent').style.display = 'block';
    }

    async function checkIfUserIsRecipientAndUpdateUI(partActions, myParticipant) {
        try {
            const response = await fetch(`${API_URL}/api/event/events/${eventId}/my-recipient`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                const currentUserId = parseInt(localStorage.getItem('user_id'));

                if (data.recipient_id === currentUserId) {
                    if (!myParticipant.gift_sent_confirmation) {
                        partActions.innerHTML += `<button class="btn btn-info" onclick="confirmGiftReceived()">
                            <i class="fas fa-check-circle"></i> Подтвердить получение подарка
                        </button>`;
                    } else {
                        partActions.innerHTML += `<span class="badge badge-success">Подарок получен и подтвержден ✅</span>`;
                    }
                } else {
                    if (!myParticipant.gift_sent_confirmation) {
                        partActions.innerHTML += `<span class="badge badge-warning">Подарок отмечен как отправленный. Ожидает подтверждения получателя</span>`;
                    } else {
                        partActions.innerHTML += `<span class="badge badge-success">Получатель подтвердил получение ✅</span>`;
                    }
                }
            }
        } catch (error) {
            console.error('Ошибка проверки получателя:', error);
        }
    }

    window.startEvent = async function () {
        if (!confirm('Начать мероприятие? После начала нельзя будет добавлять участников.')) return;
        try {
            const response = await fetch(`${API_URL}/api/event/events/${eventId}/start`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                showMessage('Мероприятие начато', 'success');
                setTimeout(() => location.reload(), 1500);
            } else {
                const err = await response.json();
                showMessage(err.detail || 'Ошибка', 'error');
            }
        } catch (error) {
            showMessage('Ошибка соединения', 'error');
        }
    };

    window.drawAssignments = async function () {
        if (!confirm('Провести жеребьевку? Это действие необратимо.')) return;
        try {
            const response = await fetch(`${API_URL}/api/event/events/${eventId}/draw`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                showMessage('Жеребьевка проведена', 'success');
                setTimeout(() => location.reload(), 1500);
            } else {
                const err = await response.json();
                showMessage(err.detail || 'Ошибка', 'error');
            }
        } catch (error) {
            showMessage('Ошибка соединения', 'error');
        }
    };

    window.completeEvent = async function () {
        if (!confirm('Завершить мероприятие?')) return;
        try {
            const response = await fetch(`${API_URL}/api/event/events/${eventId}/complete`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                showMessage('Мероприятие завершено', 'success');
                setTimeout(() => location.reload(), 1500);
            } else {
                const err = await response.json();
                showMessage(err.detail || 'Ошибка', 'error');
            }
        } catch (error) {
            showMessage('Ошибка соединения', 'error');
        }
    };

    window.editEvent = function () {
        window.location.href = `event-form.html?id=${eventId}`;
    };

    async function loadDrawInfo() {
        try {
            const response = await fetch(`${API_URL}/api/event/events/${eventId}/my-recipient`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                const data = await response.json();
                document.getElementById('drawInfo').innerHTML = `<p>🎅 Вы дарите подарок пользователю <strong>ID ${data.recipient_id}</strong>.</p>`;
            } else {
                document.getElementById('drawInfo').innerHTML = '<p>Информация о жеребьевке временно недоступна.</p>';
            }
        } catch (error) {
            console.error('Ошибка загрузки информации о жеребьевке:', error);
        }
    }

    window.markGiftSent = async function () {
        try {
            const response = await fetch(`${API_URL}/api/event/events/${eventId}/gift-sent`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ gift_sent: true })
            });
            if (response.ok) {
                showMessage('Подарок отмечен как отправленный', 'success');
                setTimeout(() => location.reload(), 1500);
            } else {
                const err = await response.json();
                showMessage(err.detail || 'Ошибка', 'error');
            }
        } catch (error) {
            showMessage('Ошибка соединения', 'error');
        }
    };

    window.confirmGiftReceived = async function () {
        if (!confirm('Подтвердить получение подарка?')) return;
        try {
            const response = await fetch(`${API_URL}/api/event/events/${eventId}/confirm-gift`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                showMessage('Получение подарка подтверждено', 'success');
                setTimeout(() => location.reload(), 1500);
            } else {
                const err = await response.json();
                showMessage(err.detail || 'Ошибка', 'error');
            }
        } catch (error) {
            showMessage('Ошибка соединения', 'error');
        }
    };

    async function loadRecipientWishlist() {
        try {
            const response = await fetch(`${API_URL}/api/event/events/${eventId}/recipient-wishlist`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.wishlist) {
                    displayRecipientWishlist(data.wishlist);
                    document.getElementById('recipientWishlistSection').style.display = 'block';
                } else if (data.wishlist_id) {
                    document.getElementById('recipientWishlistContent').innerHTML =
                        '<p>Информация о вишлисте получателя временно недоступна.</p>';
                }
            } else if (response.status === 404) {
                document.getElementById('recipientWishlistContent').innerHTML =
                    '<p>Информация о вишлисте получателя пока недоступна.</p>';
            }
        } catch (error) {
            console.error('Ошибка загрузки вишлиста получателя:', error);
        }
    }

    function displayRecipientWishlist(wishlist) {
        const container = document.getElementById('recipientWishlistContent');
        if (!container) return;

        let itemsHtml = '';
        if (wishlist.items && wishlist.items.length > 0) {
            itemsHtml = '<div class="items-grid" style="margin-top: 15px;">';
            wishlist.items.forEach(item => {
                itemsHtml += `
                    <div class="item-card">
                        <div class="item-name">${escapeHtml(item.name)}</div>
                        ${item.description ? `<div class="item-description">${escapeHtml(item.description)}</div>` : ''}
                        ${item.link ? `<a href="${item.link}" target="_blank" class="item-link"><i class="fas fa-external-link-alt"></i> Ссылка</a>` : ''}
                        ${item.price ? `<div class="item-price">💰 ${item.price} ₽</div>` : ''}
                    </div>
                `;
            });
            itemsHtml += '</div>';
        } else {
            itemsHtml = '<p>В этом вишлисте пока нет желаний.</p>';
        }

        container.innerHTML = `
            <h4 style="margin-bottom: 10px; color: var(--primary);">${escapeHtml(wishlist.name)}</h4>
            ${wishlist.description ? `<p style="margin-bottom: 15px;">${escapeHtml(wishlist.description)}</p>` : ''}
            ${itemsHtml}
        `;
    }
}

if (document.getElementById('eventForm')) {
    console.log('✅ Страница формы загружена');

    const urlParams = new URLSearchParams(window.location.search);
    const eventId = urlParams.get('id');
    console.log('ID события:', eventId);

    if (eventId) {
        document.getElementById('formTitle').textContent = 'Редактирование мероприятия';
        document.getElementById('submitBtn').textContent = 'Сохранить';
        document.getElementById('eventId').value = eventId;
        loadEventForEdit(eventId);
    }

    const form = document.getElementById('eventForm');
    console.log('Форма найдена:', form);

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        console.log('✅ Форма отправлена!');

        const name = document.getElementById('name').value;
        const description = document.getElementById('description').value;
        const startDateValue = document.getElementById('startDate').value;
        const endDateValue = document.getElementById('endDate').value;
        const deadlineValue = document.getElementById('registrationDeadline').value;

        if (!name || !startDateValue || !endDateValue || !deadlineValue) {
            showMessage('Заполните все обязательные поля', 'error');
            return;
        }

        const id = document.getElementById('eventId').value;
        const isEditing = !!id;

        const formData = {
            name: name,
            description: description || null,
            is_private: document.getElementById('isPrivate')?.checked || true,
            start_date: new Date(startDateValue).toISOString(),
            end_date: new Date(endDateValue).toISOString(),
            registration_deadline: new Date(deadlineValue).toISOString(),
            min_gift_amount: document.getElementById('minGiftAmount').value ? parseFloat(document.getElementById('minGiftAmount').value) : null,
            max_gift_amount: document.getElementById('maxGiftAmount').value ? parseFloat(document.getElementById('maxGiftAmount').value) : null
        };

        try {
            const url = isEditing ? `${API_URL}/api/event/events/${id}` : `${API_URL}/api/event/events`;
            const response = await fetch(url, {
                method: isEditing ? 'PATCH' : 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                showMessage(isEditing ? 'Мероприятие обновлено' : 'Мероприятие создано', 'success');
                setTimeout(() => window.location.href = 'events.html', 1500);
            } else {
                const error = await response.json();
                showMessage(error.detail || 'Ошибка', 'error');
            }
        } catch (error) {
            showMessage('Ошибка соединения с сервером', 'error');
        }
    });

    async function loadEventForEdit(id) {
        showLoader(true);
        try {
            const response = await fetch(`${API_URL}/api/event/events/${id}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            const event = await response.json();

            document.getElementById('name').value = event.name;
            document.getElementById('description').value = event.description || '';
            document.getElementById('startDate').value = event.start_date.slice(0, 16);
            document.getElementById('endDate').value = event.end_date.slice(0, 16);
            document.getElementById('registrationDeadline').value = event.registration_deadline.slice(0, 16);
            document.getElementById('minGiftAmount').value = event.min_gift_amount || '';
            document.getElementById('maxGiftAmount').value = event.max_gift_amount || '';

            const isPrivateCheckbox = document.getElementById('isPrivate');
            if (isPrivateCheckbox) {
                isPrivateCheckbox.checked = event.is_private;
            }
        } catch (error) {
            showMessage('Ошибка загрузки', 'error');
        } finally {
            showLoader(false);
        }
    }
}

if (document.getElementById('joinForm')) {
    const urlParams = new URLSearchParams(window.location.search);
    const eventId = urlParams.get('id');
    const eventName = urlParams.get('name');

    if (!eventId) window.location.href = 'events.html';
    if (eventName) {
        document.getElementById('eventNameHint').textContent = `Мероприятие: ${eventName}`;
    }

    loadUserWishlists();

    async function loadUserWishlists() {
        try {
            const response = await fetch(`${API_URL}/api/wishlist/wishlists`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const wishlists = await response.json();
                const select = document.getElementById('wishlistId');
                if (select) {
                    wishlists.forEach(w => {
                        const option = document.createElement('option');
                        option.value = w.id;
                        option.textContent = `${w.name} (${w.items?.length || 0} желаний)`;
                        select.appendChild(option);
                    });
                }
            }
        } catch (error) {
            console.error('Не удалось загрузить вишлисты', error);
        }
    }

    document.getElementById('joinForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const wishlistId = document.getElementById('wishlistId').value;

        try {
            const response = await fetch(`${API_URL}/api/event/events/${eventId}/join`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ wishlist_id: wishlistId || null })
            });

            if (response.ok) {
                showMessage('Вы успешно присоединились к мероприятию', 'success');
                setTimeout(() => window.location.href = `event-detail.html?id=${eventId}`, 1500);
            } else {
                const error = await response.json();
                showMessage(error.detail || 'Ошибка', 'error');
            }
        } catch (error) {
            showMessage('Ошибка соединения', 'error');
        }
    });
}

function showAddParticipantModal() {
    const modal = document.getElementById('addParticipantModal');
    if (modal) {
        document.getElementById('userId').value = '';
        document.getElementById('addParticipantMessage').style.display = 'none';
        openModal('addParticipantModal');
    } else {
        console.error('Модальное окно не найдено');
    }
}

if (document.getElementById('addParticipantForm')) {
    document.getElementById('addParticipantForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const userId = document.getElementById('userId').value;
        const urlParams = new URLSearchParams(window.location.search);
        const eventId = urlParams.get('id');

        if (!userId) {
            showModalMessage('addParticipantMessage', 'Введите ID пользователя', 'error');
            return;
        }

        try {
            const response = await fetch(`${API_URL}/api/event/events/${eventId}/add-participant`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ user_id: parseInt(userId) })
            });

            const data = await response.json();

            if (response.ok) {
                showModalMessage('addParticipantMessage', 'Пользователь добавлен', 'success');
                setTimeout(() => {
                    closeModal('addParticipantModal');
                    location.reload();
                }, 1500);
            } else {
                showModalMessage('addParticipantMessage', data.detail || 'Ошибка', 'error');
            }
        } catch (error) {
            showModalMessage('addParticipantMessage', 'Ошибка соединения', 'error');
        }
    });
}

if (document.getElementById('eventContent')) {
    var eventId = new URLSearchParams(window.location.search).get('id');
}

async function loadUserWishlistsForSelect() {
    try {
        const response = await fetch(`${API_URL}/api/wishlist/wishlists`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            const wishlists = await response.json();
            const select = document.getElementById('wishlistSelect');
            if (select) {
                select.innerHTML = '<option value="">-- Выберите вишлист --</option>';

                let currentWishlistId = null;
                try {
                    const currentResp = await fetch(`${API_URL}/api/event/events/${eventId}/my-wishlist`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    if (currentResp.ok) {
                        const currentData = await currentResp.json();
                        currentWishlistId = currentData.wishlist_id;
                    }
                } catch (e) {
                    console.log('Нет выбранного вишлиста');
                }

                wishlists.forEach(w => {
                    const option = document.createElement('option');
                    option.value = w.id;
                    option.textContent = `${w.name} (${w.items?.length || 0} желаний)`;
                    if (w.id === currentWishlistId || (w.is_primary && !currentWishlistId)) {
                        option.selected = true;
                    }
                    select.appendChild(option);
                });
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки вишлистов:', error);
    }
}

function showSelectWishlistModal() {
    loadUserWishlistsForSelect();
    const msgEl = document.getElementById('selectWishlistMessage');
    if (msgEl) msgEl.style.display = 'none';
    openModal('selectWishlistModal');
}

if (document.getElementById('selectWishlistForm')) {
    document.getElementById('selectWishlistForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const wishlistId = document.getElementById('wishlistSelect').value;
        if (!wishlistId) {
            showModalMessage('selectWishlistMessage', 'Выберите вишлист', 'error');
            return;
        }

        try {
            const response = await fetch(`${API_URL}/api/event/events/${eventId}/select-wishlist`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ wishlist_id: parseInt(wishlistId) })
            });

            if (response.ok) {
                showModalMessage('selectWishlistMessage', 'Вишлист выбран', 'success');
                setTimeout(() => {
                    closeModal('selectWishlistModal');
                    location.reload();
                }, 1500);
            } else {
                const error = await response.json();
                showModalMessage('selectWishlistMessage', error.detail || 'Ошибка', 'error');
            }
        } catch (error) {
            showModalMessage('selectWishlistMessage', 'Ошибка соединения', 'error');
        }
    });
}

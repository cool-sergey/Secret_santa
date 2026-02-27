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
    const messageDiv = document.getElementById('message');
    if (!messageDiv) return;

    messageDiv.textContent = text;
    messageDiv.className = `message ${type} show`;

    setTimeout(() => {
        messageDiv.classList.remove('show');
    }, 3000);
}

function showModalMessage(elementId, text, type) {
    const element = document.getElementById(elementId);
    if (!element) return;

    element.textContent = text;
    element.className = `message ${type} show`;
}

function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

async function loadWishlists() {
    showLoader(true);

    try {
        const response = await fetch(`${API_URL}/api/wishlist/wishlists`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.status === 401) {
            localStorage.removeItem('access_token');
            window.location.href = 'http://localhost/user/login.html';
            return;
        }

        const wishlists = await response.json();
        displayWishlists(wishlists);
    } catch (error) {
        showMessage('Ошибка загрузки', 'error');
        console.error(error);
    } finally {
        showLoader(false);
    }
}

function displayWishlists(wishlists) {
    const container = document.getElementById('wishlistsContainer');
    if (!container) return;

    if (!wishlists || wishlists.length === 0) {
        container.innerHTML = '<div class="empty-state">Нет вишлистов</div>';
        return;
    }

    let html = '<div class="wishlist-grid">';
    wishlists.forEach(wishlist => {
        html += `
            <div class="wishlist-card ${wishlist.is_primary ? 'primary' : ''}" 
                 onclick="viewWishlist(${wishlist.id})">
                ${wishlist.is_primary ? '<span class="primary-badge">Основной</span>' : ''}
                <div class="wishlist-name">${escapeHtml(wishlist.name)}</div>
                <div class="wishlist-description">${escapeHtml(wishlist.description || 'Нет описания')}</div>
            </div>
        `;
    });
    html += '</div>';
    container.innerHTML = html;
}

function viewWishlist(id) {
    window.location.href = `wishlist-detail.html?id=${id}`;
}

function editWishlist(id) {
    window.location.href = `wishlist-form.html?id=${id}`;
}

let currentWishlist = null;
let editingItemId = null;

async function loadWishlistDetail() {
    const urlParams = new URLSearchParams(window.location.search);
    const wishlistId = urlParams.get('id');

    if (!wishlistId) {
        window.location.href = 'wishlist.html';
        return;
    }

    showLoader(true);

    try {
        const response = await fetch(`${API_URL}/api/wishlist/wishlists/${wishlistId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.status === 401) {
            localStorage.removeItem('access_token');
            window.location.href = 'http://localhost/user/login.html';
            return;
        }

        if (response.status === 404) {
            showMessage('Вишлист не найден', 'error');
            setTimeout(() => window.location.href = 'wishlist.html', 2000);
            return;
        }

        const wishlist = await response.json();
        currentWishlist = wishlist;
        displayWishlistDetail(wishlist);

    } catch (error) {
        showMessage('Ошибка загрузки', 'error');
        console.error(error);
    } finally {
        showLoader(false);
    }
}

function displayWishlistDetail(wishlist) {
    document.getElementById('wishlistName').textContent = wishlist.name;
    document.getElementById('wishlistDescription').textContent = wishlist.description || 'Нет описания';
    document.getElementById('wishlistCreated').innerHTML = `<i class="fas fa-calendar"></i> Создан: ${new Date(wishlist.created_at).toLocaleDateString()}`;

    const items = wishlist.items || [];
    document.getElementById('wishlistItemsCount').innerHTML = `<i class="fas fa-gift"></i> ${items.length} желаний`;

    displayItems(items);
    document.getElementById('wishlistContent').style.display = 'block';
}

function displayItems(items) {
    const container = document.getElementById('itemsContainer');

    if (!items || items.length === 0) {
        container.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1;">
                <i class="fas fa-gift"></i>
                <p>В этом вишлисте пока нет желаний</p>
                <button class="btn btn-primary" onclick="showAddItemForm()">Добавить желание</button>
            </div>
        `;
        return;
    }

    let html = '';
    items.forEach(item => {
        html += `
            <div class="item-card">
                <div class="item-name">${escapeHtml(item.name)}</div>
                ${item.description ? `<div class="item-description">${escapeHtml(item.description)}</div>` : ''}
                ${item.link ? `
                    <a href="${item.link}" target="_blank" class="item-link">
                        <i class="fas fa-external-link-alt"></i> Ссылка
                    </a>
                ` : ''}
                ${item.price ? `
                    <div class="item-price">
                        <i class="fas fa-tag"></i> ${item.price} ₽
                    </div>
                ` : ''}
                <div class="item-actions">
                    <button class="btn-icon-sm" onclick="editItem(${item.id})" title="Редактировать">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-icon-sm" onclick="deleteItem(${item.id})" title="Удалить">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function showAddItemForm() {
    editingItemId = null;
    document.getElementById('itemModalTitle').textContent = 'Добавить желание';
    document.getElementById('itemId').value = '';
    document.getElementById('itemName').value = '';
    document.getElementById('itemLink').value = '';
    document.getElementById('itemDescription').value = '';
    document.getElementById('itemPrice').value = '';
    openModal('itemModal');
}

function editItem(id) {
    const item = currentWishlist.items.find(i => i.id === id);
    if (!item) return;

    editingItemId = id;
    document.getElementById('itemModalTitle').textContent = 'Редактировать желание';
    document.getElementById('itemId').value = item.id;
    document.getElementById('itemName').value = item.name || '';
    document.getElementById('itemLink').value = item.link || '';
    document.getElementById('itemDescription').value = item.description || '';
    document.getElementById('itemPrice').value = item.price || '';
    openModal('itemModal');
}

async function deleteItem(id) {
    if (!confirm('Удалить это желание?')) return;

    try {
        const response = await fetch(`${API_URL}/api/wishlist/wishlists/items/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            showMessage('Желание удалено', 'success');
            loadWishlistDetail();
        } else {
            const data = await response.json();
            showMessage(data.detail || 'Ошибка', 'error');
        }
    } catch (error) {
        showMessage('Ошибка соединения', 'error');
    }
}

function closeItemModal() {
    closeModal('itemModal');
}

if (document.getElementById('itemForm')) {
    document.getElementById('itemForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const wishlistId = new URLSearchParams(window.location.search).get('id');
        const itemId = document.getElementById('itemId').value;
        const isEditing = !!itemId;

        const itemData = {
            name: document.getElementById('itemName').value,
            link: document.getElementById('itemLink').value || null,
            description: document.getElementById('itemDescription').value || null,
            price: document.getElementById('itemPrice').value ? parseFloat(document.getElementById('itemPrice').value) : null
        };

        try {
            let url = isEditing
                ? `${API_URL}/api/wishlist/wishlists/items/${itemId}`
                : `${API_URL}/api/wishlist/wishlists/${wishlistId}/items`;

            const response = await fetch(url, {
                method: isEditing ? 'PATCH' : 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(itemData)
            });

            if (response.ok) {
                closeItemModal();
                loadWishlistDetail();
                showMessage(isEditing ? 'Желание обновлено' : 'Желание добавлено', 'success');
            } else {
                const error = await response.json();
                showModalMessage('itemMessage', error.detail || 'Ошибка', 'error');
            }
        } catch (error) {
            showModalMessage('itemMessage', 'Ошибка соединения', 'error');
        }
    });
}

if (document.getElementById('itemsContainer')) {
    loadWishlistDetail();
}

async function setPrimary(id) {
    if (!confirm('Сделать этот вишлист основным?')) return;

    try {
        const response = await fetch(`${API_URL}/api/wishlist/wishlists/${id}/set-primary`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            showMessage('Основной вишлист изменен', 'success');
            loadWishlists();
        } else {
            const data = await response.json();
            showMessage(data.detail || 'Ошибка', 'error');
        }
    } catch (error) {
        showMessage('Ошибка соединения', 'error');
    }
}

async function deleteWishlist(id) {
    if (!confirm('Удалить вишлист? Все желания также будут удалены.')) return;

    try {
        const response = await fetch(`${API_URL}/api/wishlist/wishlists/${id}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            showMessage('Вишлист удален', 'success');
            loadWishlists();
        } else {
            const data = await response.json();
            showMessage(data.detail || 'Ошибка', 'error');
        }
    } catch (error) {
        showMessage('Ошибка соединения', 'error');
    }
}

async function loadWishlistForEdit() {
    const urlParams = new URLSearchParams(window.location.search);
    const id = urlParams.get('id');

    if (!id) return;

    document.getElementById('formTitle').textContent = 'Редактирование вишлиста';
    document.getElementById('submitBtn').textContent = 'Сохранить';
    document.getElementById('wishlistId').value = id;

    showLoader(true);
    try {
        const response = await fetch(`${API_URL}/api/wishlist/wishlists/${id}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const wishlist = await response.json();

        document.getElementById('name').value = wishlist.name;
        document.getElementById('description').value = wishlist.description || '';
        document.getElementById('isPrimary').checked = wishlist.is_primary;
    } catch (error) {
        showMessage('Ошибка загрузки', 'error');
    } finally {
        showLoader(false);
    }
}

if (document.getElementById('wishlistsContainer')) {
    loadWishlists();
}

if (document.getElementById('wishlistForm')) {
    loadWishlistForEdit();

    document.getElementById('wishlistForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const id = document.getElementById('wishlistId').value;
        const isEditing = !!id;

        const data = {
            name: document.getElementById('name').value,
            description: document.getElementById('description').value || null,
            is_primary: document.getElementById('isPrimary').checked
        };

        try {
            const url = isEditing
                ? `${API_URL}/api/wishlist/wishlists/${id}`
                : `${API_URL}/api/wishlist/wishlists`;

            const response = await fetch(url, {
                method: isEditing ? 'PATCH' : 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                showMessage(isEditing ? 'Вишлист обновлен' : 'Вишлист создан', 'success');
                setTimeout(() => window.location.href = 'wishlist.html', 1000);
            } else {
                const error = await response.json();
                showMessage(error.detail || 'Ошибка', 'error');
            }
        } catch (error) {
            showMessage('Ошибка соединения', 'error');
        }
    });
}

function goToProfile() {
    window.location.href = 'http://localhost/user/profile.html';
}

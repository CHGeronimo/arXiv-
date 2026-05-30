// js/subscriptions.js
let subscriptions = { arxiv: { categories: [] }, crossref: { journals: [] } };

const ARXIV_CATEGORIES = [
    "cs.AI", "cs.CL", "cs.CV", "cs.LG", "cs.RO", "cs.NE", "cs.MM",
    "cs.CR", "cs.IR", "cs.HC", "cs.DB", "cs.DC", "cs.SE", "cs.SY",
    "eess.SP", "eess.IV", "eess.AS",
    "math.OC", "math.ST", "stat.ML", "stat.AP",
    "physics.optics", "physics.app-ph", "physics.med-ph",
    "q-bio.NC", "q-bio.QM",
];

async function loadSubscriptions() {
    try {
        const resp = await fetch('/api/subscriptions');
        if (resp.ok) {
            subscriptions = await resp.json();
        }
    } catch (e) {
        console.error('Failed to load subscriptions:', e);
        const saved = localStorage.getItem('subscriptions');
        if (saved) subscriptions = JSON.parse(saved);
    }
    renderSubscriptionUI();
    return subscriptions;
}

async function saveSubscriptions(newSubs) {
    subscriptions = newSubs;
    localStorage.setItem('subscriptions', JSON.stringify(newSubs));
    try {
        const resp = await fetch('/api/subscriptions', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newSubs),
        });
        if (resp.ok) {
            fetch('/api/trigger/arxiv', { method: 'POST' }).catch(() => {});
            fetch('/api/trigger/crossref', { method: 'POST' }).catch(() => {});
        }
    } catch (e) {
        console.error('Failed to save subscriptions to server:', e);
    }
}

function renderSubscriptionUI() {
    renderArxivCategories();
    renderCrossrefJournals();
}

function renderArxivCategories() {
    const container = document.getElementById('arxiv-categories-chips');
    if (!container) return;
    const selected = new Set(subscriptions.arxiv.categories);
    container.innerHTML = ARXIV_CATEGORIES.map(cat => `
        <label class="sub-chip ${selected.has(cat) ? 'selected' : ''}" data-cat="${cat}">
            <input type="checkbox" ${selected.has(cat) ? 'checked' : ''}
                   onchange="toggleArxivCategory('${cat}', this.checked)">
            ${cat}
        </label>
    `).join('');
}

function toggleArxivCategory(cat, checked) {
    const cats = new Set(subscriptions.arxiv.categories);
    if (checked) cats.add(cat); else cats.delete(cat);
    subscriptions.arxiv.categories = [...cats].sort();
    saveSubscriptions(subscriptions);
    renderArxivCategories();
}

function renderCrossrefJournals() {
    const container = document.getElementById('crossref-journals-list');
    if (!container) return;
    if (!subscriptions.crossref.journals.length) {
        container.innerHTML = '<p class="empty-hint">No journals subscribed yet. Search above to add.</p>';
        return;
    }
    container.innerHTML = subscriptions.crossref.journals.map(j => `
        <div class="journal-item">
            <span class="journal-name">${j.name}</span>
            <span class="journal-issn">${j.issn}</span>
            <button class="unfollow-btn" onclick="unfollowJournal('${j.issn}')">Unfollow</button>
        </div>
    `).join('');
}

function unfollowJournal(issn) {
    subscriptions.crossref.journals = subscriptions.crossref.journals.filter(
        j => j.issn !== issn
    );
    saveSubscriptions(subscriptions);
    renderCrossrefJournals();
}

function openSubscriptionModal() {
    document.getElementById('subscription-modal').classList.add('active');
    loadSubscriptions();
}

function closeSubscriptionModal() {
    document.getElementById('subscription-modal').classList.remove('active');
}

function switchSubTab(tab, el) {
    document.querySelectorAll('.sub-tab').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
    document.getElementById('sub-tab-arxiv').style.display = tab === 'arxiv' ? 'block' : 'none';
    document.getElementById('sub-tab-crossref').style.display = tab === 'crossref' ? 'block' : 'none';
}

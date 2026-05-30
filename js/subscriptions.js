// js/subscriptions.js
let subscriptions = { arxiv: { categories: [] }, crossref: { journals: [] }, conferences: [], search: { keywords: [], useProfile: true } };

const ARXIV_CATEGORIES = [
    "cs.AI", "cs.CL", "cs.CV", "cs.LG", "cs.RO", "cs.NE", "cs.MM",
    "cs.CR", "cs.IR", "cs.HC", "cs.DB", "cs.DC", "cs.SE", "cs.SY",
    "eess.SP", "eess.IV", "eess.AS",
    "math.OC", "math.ST", "stat.ML", "stat.AP",
    "physics.optics", "physics.app-ph", "physics.med-ph",
    "q-bio.NC", "q-bio.QM",
];

const CONFERENCES = [
    { venue: "CVPR", label: "CVPR", group: "CV" },
    { venue: "ICCV", label: "ICCV", group: "CV" },
    { venue: "ECCV", label: "ECCV", group: "CV" },
    { venue: "NeurIPS", label: "NeurIPS", group: "ML" },
    { venue: "ICML", label: "ICML", group: "ML" },
    { venue: "ICLR", label: "ICLR", group: "ML" },
    { venue: "ACL", label: "ACL", group: "NLP" },
    { venue: "EMNLP", label: "EMNLP", group: "NLP" },
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
    if (!subscriptions.conferences) subscriptions.conferences = [];
    if (!subscriptions.search) subscriptions.search = { keywords: [], useProfile: true };
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
    renderCrossrefJournals();
    renderConferenceChips();
}

function renderConferenceChips() {
    const container = document.getElementById('conference-chips');
    if (!container) return;
    const selected = new Set((subscriptions.conferences || []).map(c => c.venue));
    let html = '';
    let currentGroup = '';
    for (const conf of CONFERENCES) {
        if (conf.group !== currentGroup) {
            if (currentGroup) html += '<div style="height:8px"></div>';
            html += `<div style="font-size:0.75rem;color:var(--text-secondary);margin-bottom:4px">${conf.group}</div>`;
            currentGroup = conf.group;
        }
        const sel = selected.has(conf.venue);
        html += `<label class="sub-chip ${sel ? 'selected' : ''}" style="display:inline-block;margin:2px 4px">
            <input type="checkbox" ${sel ? 'checked' : ''} onchange="toggleConference('${conf.venue}', this.checked)">
            ${conf.label}
        </label>`;
    }
    container.innerHTML = html;
}

function toggleConference(venue, checked) {
    if (!subscriptions.conferences) subscriptions.conferences = [];
    if (checked) {
        if (!subscriptions.conferences.some(c => c.venue === venue)) {
            subscriptions.conferences.push({ venue, lastUpdated: null });
        }
    } else {
        subscriptions.conferences = subscriptions.conferences.filter(c => c.venue !== venue);
    }
    saveSubscriptions(subscriptions);
    renderConferenceChips();
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
    ['journals', 'conferences', 'search'].forEach(t => {
        const tabEl = document.getElementById(`sub-tab-${t}`);
        if (tabEl) tabEl.style.display = t === tab ? 'block' : 'none';
    });
}

function toggleCustomKeywords() {
    const useProfile = document.getElementById('use-profile-keywords').checked;
    document.getElementById('custom-keywords').style.display = useProfile ? 'none' : 'block';
}

async function saveSearchKeywords() {
    const useProfile = document.getElementById('use-profile-keywords').checked;
    if (useProfile) {
        subscriptions.search = { keywords: [], useProfile: true };
    } else {
        const text = document.getElementById('custom-keywords').value;
        const keywords = text.split('\n').map(k => k.trim()).filter(k => k);
        subscriptions.search = { keywords, useProfile: false };
    }
    await saveSubscriptions(subscriptions);
    fetch('/api/trigger/s2', { method: 'POST' }).catch(() => {});
}

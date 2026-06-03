// js/crossref-search.js
const CROSSREF_JOURNALS_API = 'https://api.crossref.org/journals';

let searchDebounce = null;

async function searchJournals(query) {
    if (!query || query.length < 2) return [];
    const url = `${CROSSREF_JOURNALS_API}?query=${encodeURIComponent(query)}&rows=20&mailto=daily-arxiv@proton.me`;
    try {
        const resp = await fetch(url);
        if (!resp.ok) return [];
        const data = await resp.json();
        return (data.message?.items || []).map(item => ({
            title: item.title || 'Unknown',
            issn: (item.ISSN || [])[0] || '',
            all_issn: (item.ISSN || []).join(', '),
            publisher: item.publisher || '',
            subjects: (item.subjects || []).map(s => s.name).join(', '),
        }));
    } catch (e) {
        console.error('Journal search failed:', e);
        return [];
    }
}

function isJournalFollowed(issn) {
    return subscriptions.crossref.journals.some(j => j.issn === issn);
}

function handleJournalSearch() {
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(async () => {
        const input = document.getElementById('journal-search-input');
        const results = document.getElementById('journal-search-results');
        const query = input.value.trim();
        if (!query) { results.innerHTML = ''; return; }

        results.innerHTML = '<p style="color:var(--text-2)">Searching...</p>';
        const journals = await searchJournals(query);

        if (!journals.length) {
            results.innerHTML = '<p class="empty-hint">No journals found.</p>';
            return;
        }

        results.innerHTML = journals.map(j => {
            const followed = isJournalFollowed(j.issn);
            return `
                <div class="journal-item">
                    <div>
                        <span class="journal-name">${j.title}</span>
                        <span class="journal-issn">${j.all_issn || j.issn}</span>
                        <div style="font-size:0.75rem;color:var(--text-2)">${j.publisher}${j.subjects ? ' · ' + j.subjects : ''}</div>
                    </div>
                    <button class="${followed ? 'unfollow-btn' : 'follow-btn'}"
                            data-action="${followed ? 'unfollow' : 'follow'}"
                            data-issn="${j.issn}"
                            data-name="${j.title.replace(/"/g, '&quot;').replace(/</g, '&lt;')}">
                        ${followed ? 'Unfollow' : 'Follow'}
                    </button>
                </div>
            `;
        }).join('');

        results.querySelectorAll('button[data-action]').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                const issn = btn.dataset.issn;
                if (action === 'unfollow') {
                    unfollowJournal(issn);
                    handleJournalSearch();
                } else {
                    followJournal(issn, btn.dataset.name);
                }
            });
        });
    }, 300);
}

async function followJournal(issn, name) {
    if (isJournalFollowed(issn)) return;
    subscriptions.crossref.journals.push({
        issn: issn,
        name: name,
        lastUpdated: null,
    });
    await saveSubscriptions(subscriptions, 'crossref');
    renderCrossrefJournals();
    handleJournalSearch();
}

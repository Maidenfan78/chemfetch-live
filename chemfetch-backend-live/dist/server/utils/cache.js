// utils/cache.ts
export class TTLCache {
    ttl;
    store = new Map();
    constructor(ttlMs) {
        this.ttl = ttlMs;
    }
    get(key) {
        const entry = this.store.get(key);
        if (!entry)
            return undefined;
        if (Date.now() > entry.expiresAt) {
            this.store.delete(key);
            return undefined;
        }
        return entry.value;
    }
    set(key, value) {
        this.store.set(key, { value, expiresAt: Date.now() + this.ttl });
    }
    has(key) {
        const entry = this.store.get(key);
        return !!entry && Date.now() <= entry.expiresAt;
    }
    clear() {
        this.store.clear();
    }
    delete(key) {
        this.store.delete(key);
    }
    size() {
        return this.store.size;
    }
}

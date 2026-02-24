/**
 * Client-side encryption/decryption for Cryptic Notes
 * Matches the server-side Python implementation in crypto.py
 */

class CryptoService {
    /**
     * Normalize mnemonic phrase (trim, lowercase, normalize whitespace)
     */
    static normalizeMnemonic(mnemonic) {
        return mnemonic.trim().toLowerCase().replace(/\s+/g, ' ');
    }

    /**
     * Derive AES key from mnemonic using SHA256
     */
    static async deriveKey(mnemonic) {
        const normalized = this.normalizeMnemonic(mnemonic);
        const encoder = new TextEncoder();
        const data = encoder.encode(normalized);
        const hashBuffer = await crypto.subtle.digest('SHA-256', data);
        return hashBuffer;
    }

    /**
     * Decrypt a note using AES-256-CBC
     */
    static async decryptNote(ciphertext, iv, mnemonic) {
        try {
            const key = await this.deriveKey(mnemonic);
            const ciphertextBytes = this.base64ToBytes(ciphertext);
            const ivBytes = this.base64ToBytes(iv);

            // Import the key for AES-CBC decryption
            const cryptoKey = await crypto.subtle.importKey(
                'raw',
                key,
                { name: 'AES-CBC' },
                false,
                ['decrypt']
            );

            // Decrypt (Web Crypto API automatically removes PKCS7 padding)
            const decryptedBuffer = await crypto.subtle.decrypt(
                {
                    name: 'AES-CBC',
                    iv: ivBytes,
                },
                cryptoKey,
                ciphertextBytes
            );

            // Web Crypto API automatically handles PKCS7 padding removal
            const decoder = new TextDecoder();
            const jsonString = decoder.decode(decryptedBuffer);
            return JSON.parse(jsonString);
        } catch (error) {
            console.error('Decryption error:', error);
            throw new Error('Failed to decrypt note: ' + error.message);
        }
    }

    /**
     * Encrypt a note using AES-256-CBC
     */
    static async encryptNote(title, body, mnemonic) {
        try {
            const key = await this.deriveKey(mnemonic);
            const payload = JSON.stringify({ title, body });
            const encoder = new TextEncoder();
            const payloadBytes = encoder.encode(payload);

            // Add PKCS7 padding
            const padded = this.addPKCS7Padding(payloadBytes);

            // Generate random IV
            const ivBytes = crypto.getRandomValues(new Uint8Array(16));

            // Import the key for AES-CBC encryption
            const cryptoKey = await crypto.subtle.importKey(
                'raw',
                key,
                { name: 'AES-CBC' },
                false,
                ['encrypt']
            );

            // Encrypt
            const encryptedBuffer = await crypto.subtle.encrypt(
                {
                    name: 'AES-CBC',
                    iv: ivBytes,
                },
                cryptoKey,
                padded
            );

            const ciphertext = this.bytesToBase64(new Uint8Array(encryptedBuffer));
            const iv = this.bytesToBase64(ivBytes);
            return { ciphertext, iv };
        } catch (error) {
            console.error('Encryption error:', error);
            throw new Error('Failed to encrypt note: ' + error.message);
        }
    }

    /**
     * Add PKCS7 padding
     */
    static addPKCS7Padding(data) {
        const blockSize = 16;
        const paddingLength = blockSize - (data.length % blockSize);
        const padded = new Uint8Array(data.length + paddingLength);
        padded.set(data);
        padded.fill(paddingLength, data.length);
        return padded;
    }

    /**
     * Remove PKCS7 padding
     */
    static removePKCS7Padding(data) {
        if (data.length === 0) {
            throw new Error('Invalid padding: empty data');
        }
        const paddingLength = data[data.length - 1];
        if (paddingLength > 16 || paddingLength === 0) {
            throw new Error('Invalid padding length');
        }
        // Verify padding bytes are all the same
        for (let i = data.length - paddingLength; i < data.length; i++) {
            if (data[i] !== paddingLength) {
                throw new Error('Invalid padding bytes');
            }
        }
        return data.slice(0, data.length - paddingLength);
    }

    /**
     * Convert base64 string to Uint8Array
     */
    static base64ToBytes(base64) {
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }
        return bytes;
    }

    /**
     * Convert Uint8Array to base64 string
     */
    static bytesToBase64(bytes) {
        let binary = '';
        for (let i = 0; i < bytes.length; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }
}

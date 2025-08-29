# 🚀 ChemFetch Website Deployment Guide

## Issue: "chemfetch.com is almost here!" showing instead of your website

Your domain is showing DreamHost's default page because your website files haven't been uploaded yet.

## 📁 Files to Upload to DreamHost

Upload ALL these files from your `chemfetch.com` folder to your DreamHost domain's public directory:

### Required Files:
- `index.html` - Main homepage
- `help.html` - Help & instructions page (newly created)
- `privacy-policy.html` - Privacy policy page
- `404.html` - Custom 404 error page
- `robots.txt` - Search engine crawling instructions
- `sitemap.xml` - Site structure for search engines
- `favicon.ico` - Website icon (create from favicon-generator.html)
- `favicon.svg` - Vector version of favicon

## 🔧 How to Deploy to DreamHost

### Method 1: DreamHost File Manager (Easiest)
1. Log into your DreamHost Panel
2. Navigate to **Files** → **File Manager**
3. Select your `chemfetch.com` domain
4. Upload all files to the root directory (where you see the "coming soon" files)
5. Replace any existing files when prompted

### Method 2: FTP/SFTP Upload
1. Use FTP client like FileZilla or WinSCP
2. Connect to your DreamHost server
3. Upload files to: `/home/username/chemfetch.com/`
4. Make sure `index.html` is in the root directory

### Method 3: Git Deployment (Advanced)
1. Connect to DreamHost via SSH
2. Clone your repository into the domain directory
3. Set up automatic deployments

## 🎯 After Upload

### Immediate Steps:
1. Visit https://chemfetch.com - should show your actual website
2. Test https://chemfetch.com/help - should show new help page  
3. Test https://chemfetch.com/privacy-policy.html

### Update Sitemap (sitemap.xml):
Add the new help page to your sitemap:

```xml
<url>
    <loc>https://chemfetch.com/help</loc>
    <lastmod>2025-01-01</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
</url>
```

## 🔍 Google Search Console

After uploading, submit your updated sitemap to Google:
1. Go to Google Search Console
2. Add https://chemfetch.com/sitemap.xml
3. Request re-indexing of your pages

## 📧 Domain Email Setup

If you haven't set up domain emails yet:
1. In DreamHost Panel: **Email** → **Manage Email**
2. Create: support@chemfetch.com, privacy@chemfetch.com
3. Update contact forms to use these emails

## ✅ Verification Checklist

- [ ] Upload all website files to DreamHost
- [ ] Verify chemfetch.com loads your actual website
- [ ] Test help page at chemfetch.com/help
- [ ] Check favicon appears in browser tab
- [ ] Update sitemap.xml with new help page
- [ ] Submit updated sitemap to Google
- [ ] Set up domain email addresses

## 🆘 Troubleshooting

**Still seeing "almost here" page?**
- Clear browser cache (Ctrl+F5)
- Check files are in correct directory
- Verify index.html is in root folder
- Wait 5-10 minutes for changes to propagate

**404 errors?**
- Check file names match exactly (case sensitive)
- Ensure .html extensions are included
- Verify file permissions are set correctly

**Need help?**
- Contact DreamHost support
- Check DreamHost knowledge base
- Use DreamHost's website builder if needed

---

*Once uploaded, your professional ChemFetch website will be live and searchable on Google!*
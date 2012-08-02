function (doc) {
    if (doc.doc_type === 'MobileBackend') {
        doc.domain.forEach(function (domain) {
            emit(domain, null);
        })
    }
}
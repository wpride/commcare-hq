function (doc) {
	if (doc.doc_type == 'EnqueuedMessage') {
		emit((new Date(doc.sent_at)).getTime(), null);
	}
}
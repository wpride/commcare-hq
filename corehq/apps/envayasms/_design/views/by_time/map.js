function (doc) {
	if (doc.doc_type == 'EnqueuedMessage') {
		emit(doc.sent_at, null);
	}
}
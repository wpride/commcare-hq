function (doc) {
	if (doc.doc_type == 'EnqueuedMessage') {
		emit(doc.backend_id, null);
	}
}
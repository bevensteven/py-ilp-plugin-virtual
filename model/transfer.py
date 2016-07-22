def equals(left, right):
	return (
		left and \
		right and \
		left['id'] == right['id'] and \
		left['amount'] == right['amount'] and \
		left['executionCondition'] == right['executionCondition'] and \
		left['cancellationCondition'] == right['cancellationCondition']
		)
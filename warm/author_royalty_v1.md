UFCPS Author Royalty v1

1. Purpose

UFCPS Level 2 may include a transparent author royalty mechanism for the originator of the architecture and protocol.

The royalty is intended to compensate the author for the intellectual creation and continued development of the UFCPS framework.

The royalty must remain:

explicit;

auditable;

machine-readable;

proportional;

independent of task outcomes;

separate from compute-provider compensation.

2. Proposed Rate

The proposed author royalty is:

0.001% of every qualifying transaction.

Equivalent forms:

0.001%
=
1 / 100,000
=
0.00001

The royalty is calculated independently for each transaction:

royalty_amount = transaction_amount × 0.00001

Example:

transaction = 1,000 units
royalty     = 0.01 units

transaction = 1,000,000 units
royalty     = 10 units

The royalty therefore scales automatically with transaction size.

It is not calculated from:

annual network turnover;

provider profit;

compute cost;

task value;

research result value.

The transaction itself is the accounting event that creates the royalty obligation.

3. Recipient

Proposed payout destination:

PayPal:
deivulgaris@gmail.com

This destination is an externally provided payout address and should be treated as configuration data, not as a protocol identity.

A future deployment may use another settlement mechanism or multiple payout destinations if the economic protocol requires it.

3A. Transaction-Level Mechanism

The proposed mechanism is a small protocol-level charge attached to each qualifying transaction.

Transaction
    |
    +---- network/resource settlement
    |
    +---- author royalty: 0.001%

The royalty should be accounted for separately from the economic purpose of the transaction.

For example, a compute payment may simultaneously record:

compute_provider_amount
network_fee
author_royalty

The exact fee composition remains an economic and implementation question.

4. Separation of Economic Roles

Author royalty must remain distinct from:

Compute Compensation
    = payment for verified computational resources

Validator Compensation
    = payment for verification work

Research / Task Bounty
    = optional funding attached to a research objective

Provider Revenue
    = economic return to resource providers

Author Royalty
    = compensation for the original UFCPS architecture and authorship

These flows must not be silently combined.

5. Accounting Rule

For every qualifying transaction, the system should be able to record:

royalty_event_id
source_transaction_id
transaction_amount
royalty_rate
royalty_amount
currency
recipient
timestamp
status
provenance

The calculation must be deterministic and reproducible:

royalty_amount = transaction_amount × royalty_rate

The transaction ledger should make it possible to verify that the royalty was calculated exactly once for each qualifying transaction.

Example:

settlement_base = 1,000,000 units
royalty_rate    = 0.00001
royalty_amount  = 10 units

The calculation must be deterministic.

6. Transparency

The royalty should be disclosed in the economic protocol before participants transact.

Participants should be able to determine:

what creates the royalty;

what amount is charged;

who receives it;

how it is calculated;

how it is recorded;

whether it can change;

under what governance process it could change.

The royalty should never be hidden inside an unexplained exchange rate or resource price.

7. Cap and Governance

The initial proposed rate is fixed at:

0.001%

Any future change should require an explicit protocol-governance event.

The system should not allow an agent, investor, resource provider, or administrator to silently increase the author's percentage.

8. Relation to Distributed Swarm Intelligence

The author royalty does not give the author control over the swarm.

It does not grant:

task priority;

resource ownership;

validator authority;

governance control beyond whatever explicit governance rights the protocol separately defines;

ownership of participant resources.

The royalty is an economic claim defined by protocol.

9. Implementation Questions

Before deployment, the swarm's economic research program should determine:

which transaction classes are subject to the royalty;

treatment of refunds and disputed transactions;

treatment of failed, reversed, or partially completed transactions;

minimum payout threshold;

payout frequency or accumulation policy;

interaction with network transaction fees;

currency conversion, if required;

accounting treatment across multiple jurisdictions;

legal and tax implications;

whether the destination should eventually be a controlled wallet, legal entity, or other settlement mechanism.

These are unresolved implementation questions.

10. Design Principle

The author should be compensated transparently for the creation and development of the protocol, while remaining economically and structurally distinct from the participants who provide compute, capital, validation, or other resources.

The proposed author royalty is therefore a small, explicit protocol charge rather than a discretionary payment.

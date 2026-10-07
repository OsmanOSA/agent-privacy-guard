# User feedback: invisible notification and nested pseudonyms

The installed log contains accepted/card_rendered entries, but the user saw no
notification. A synthetic native probe reproduced a visible HWND only 2 pixels
high: the Window desired size was used before content measurement. Measure the
card content and require usable native dimensions before reporting success.

Recognize narrowly defined external placeholders such as PERSON_001 and
[EMAIL_001]. Do not classify their literal spans as personal data, including when
a previous session mapping already learned them as names. Preserve masking of
adjacent personal values and credential detection; no blanket file exemption.
Keep historical mappings restorable. Use synthetic regression cases and the
same benchmark corpus/modes before and after. Redeploy verified changes globally
with app/settings backup and unchanged existing vault bytes.

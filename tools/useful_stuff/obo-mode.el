;; obo-mode.el --- a major mode for editing dna sequences
;;
;; ~/lib/emacs/jhg-lisp/obo-mode.el ---
;;
;; $Id: obo-mode.el,v 1.2 2004/09/07 23:50:55 cmungall Exp $
;;
;; Author:  harley@bcm.tmc.edu
;; URL:     http://www.hgsc.bcm.tmc.edu/~harley/elisp/obo-mode.el
;;

;;; Commentary:
;; --------------------
;; A collection of functions for editing DNA sequences.  It
;; provides functions to make editing easier.
;;
;; obo-mode will:
;;  * Fontify keywords and line numbers in sequences, but not bases.
;;  * Incrementally search dna over pads and numbers
;;  * Complement and reverse complement a region.
;;  * Move over bases and entire sequences.
;;  * Detect sequence files by content.

;;; Installation:
;; --------------------
;; Here are two suggested ways for installing this package.
;; You can choose to autoload it when needed, or load it
;; each time emacs is started.  Put one of the following
;; sections in your .emacs:
;;
;; ---Autoload:
;;  (autoload 'obo-mode "obo-mode" "Major mode for dna" t)
;;  (add-to-list
;;     'auto-mode-alist
;;     '("\\.\\(fasta\\|fa\\|exp\\|ace\\|gb\\)\\'" . obo-mode))
;;  (add-hook 'obo-mode-hook 'turn-on-font-lock)
;;
;; ---Load:
;;  (setq obo-do-setup-on-load t)
;;  (load "/pathname/obo-mode")

;;; Code:

;; Setup
(defvar obo-mode-hook nil
  "*Hook to setup `obo-mode'.")

(defvar obo-mode-load-hook nil
  "*Hook to run when `obo-mode' is loaded.")

(defvar obo-setup-on-load nil
  "*If not nil setup obo mode on load by running `obo-`add-hook's'.")

(defvar obo-namespace "unknown"
  "*ontology/namespace.")

(defvar obo-db-prefix "anon"
  "*database/authority name")

(defvar obo-id-length 7
  "*number of digits in ID; set to 0 for no padding")

(defvar obo-last-id 0
  "*database identifier incremental counter")


;; I also use "Alt" as C-c is too much to type for cursor motions.
(defvar obo-mode-map
  (let ((map (make-sparse-keymap)))
    ;; Ctrl bindings
    (define-key map "\C-cc"	'obo-add-term)
    ;; XEmacs does not like the Alt bindings
;;    (cond ((not running-xemacs)
;;      (define-key map [A-right]	'obo-add-term)))
    map)
  "The local keymap for `obo-mode'.")

;;;###autoload
(defun obo-mode ()
  "Major mode for editing OBO.

This mode also customizes isearch to search over line breaks.

\\{obo-mode-map}"
  (interactive)
  ;;
  (kill-all-local-variables)
  (setq mode-name "obo")
  (setq major-mode 'obo-mode)
  (use-local-map obo-mode-map)
  ;;
  (make-local-variable 'font-lock-defaults)
  (setq font-lock-defaults '(obo-font-lock-keywords))
  ;;
  (run-hooks 'obo-mode-hook)
  )


;; Keywords
;; Todo: Seperate the keywords into a list for each format, rather
;; than one for all.
(defvar obo-font-lock-keywords
  '(
    ;; Term definitions
    ("\\(Term\\)"
     (1 font-lock-function-name-face nil t)
     )
    ("\\(\\[Typedef\\]\\)"
     (1 font-lock-function-name-face nil t)
     )
    ("\\(\\[[a-zA-Z_]+\\]\\)"
     (1 font-lock-function-name-face nil t)
     )
    ("^\\(id:\\) +\\(.+\\)"
     (1 font-lock-keyword-face) (2 font-lock-reference-face))
    ("^\\(is_a:\\) +\\(.+\\)"
     (1 font-lock-keyword-face) (2 font-lock-reference-face))
    ("^\\(definition:\\) +\\(.+\\)"
     (1 font-lock-keyword-face) (2 font-lock-comment-face))
;;    ("^\\([-a-zA-Z_0-9]+:\\)"
;;     (1 font-lock-function-name-face)
;;     )
;;    ("^\\(relationship:\\) +\\(.+\\) +\\(.+\\)"
    ("^\\(relationship:\\) +\\([a-zA-Z_]+\\) +\\(.+\\)"
     (1 font-lock-keyword-face) (2 font-lock-function-name-face) (3 font-lock-reference-face))
;;    ("^\\([-a-zA-Z_0-9]+:\\)"
;;     (1 font-lock-function-name-face)
;;     )
    ("^\\([a-zA-A_]+:\\) +\\(.+\\)"
     (1 font-lock-keyword-face) (2 font-lock-comment-face))
    ("\\(\\!.*\\)"
     (1 font-lock-comment-face nil t)
     )
;    ("\\(\".*\"\\)"
;     (1 font-lock-comment-face nil t)
;     )
     
    "is_a:"
    "name:"
    "relationship:"
    "definition:"
    "namespace:"
    "synonym:"
    "exact_synonym:"
    )
  "Expressions to hilight in `obo-mode'.")

;; Sequence
(defvar obo-start-regexp
  "^\\(begin-ontology\\)"
  "A regexp which matches the start of an ontology.")


;;; Setup functions
(defun obo-find-file-func ()
  "Invoke `obo-mode' if the buffer look like an ontology.
and another mode is not active.
This function is added to `find-file-hooks'."
  (if (and (eq major-mode 'fundamental-mode)
	   (looking-at obo-start-regexp))
      (obo-mode)))

;;;###autoload
(defun obo-add-hooks ()
  "Add a default set of obo-hooks.
These hooks will activate `obo-mode' when visiting a file
which has a obo-like name (.obo) or whose contents
looks like obo.  It will also turn enable fontification for `obo-mode'."
  (add-hook 'obo-mode-hook 'turn-on-font-lock)
  (add-hook 'find-file-hooks 'obo-find-file-func)
  (add-to-list
   'auto-mode-alist
   '("\\.\\(obo\\)\\'" . obo-mode))
  )

;; Setup hooks on request when this mode is loaded.
(if obo-setup-on-load
    (obo-add-hooks))

(defun obo-new-term (term-name namespace term-def isa-list restr-list)
  "defines a new term"
  (setq obo-last-id (+ obo-last-id 1))
  (format 
   "[Term]\nid: %s:%07d\nname: %s\nnamespace: %s\ndefinition: \"%s\"\n%s%s\n" 
   obo-db-prefix
   obo-last-id
   term-name 
   namespace
   term-def
   (apply
    'concat
    (mapcar
     (function (lambda (n) (format "is_a: %s\n" n)))
     isa-list))
   (apply
    'concat
    (mapcar
     (function (lambda (r) 
                 (format "relationship: %s %s\n" 
                         (car r) (cadr r))))
     restr-list))
   ))


(defun obo-new-typedef (id)
  "defines a new typdef"
  (format 
   "[Typedef]\nid: %s\nname: %s\n"
   id
   id
   ))

(defun obo-new-header (namespace)
  "adds a header and sets namespace"
  (format 
   "\nformat-version: 1.0\ndate :\nsaved-by :\ndefault-namespace: %s\nremark: \n\n"
   namespace
   ))

(defun obo-new-instance (inst-name term related-list)
  "defines a new instance"
  (format 
   "\ninstance-of %s %s\n%s" 
   inst-name 
   term
   (apply
    'concat
    (mapcar
     (function (lambda (r) 
                 (format "related %s %s %s\n" 
                         (car r) inst-name (cadr r))))
     related-list))
   ))

(defun obo-setup (namespace db-prefix)
  "initalises vars"
  (interactive "snamespace: \nsdb-prefix: ")
  (setq obo-namespace namespace)
  (setq obo-db-prefix db-prefix))


(defun obo-add-term (term-name term-def)
  "Adds a term"
  (interactive "sTerm Name: \nsTerm Def: ")
  (obo-insert-term term-name obo-namespace term-def))

(defun obo-add-term-ext (term-name namespace term-def)
  "Adds a term"
  (interactive "sTerm Name: \nsNamespace: \nsTerm Def: ")
  (obo-insert-term term-name namespace term-def))

(defun obo-insert-term (term-name namespace term-def)
  (let (isa
        relationship-name
        relationship-term
        isa-list 
        relationship-list)
    (setq isa-list '())
    (setq relationship-list '())
    (while (progn
             (setq isa (read-string "is_a:"))
             (and
              (> (length isa) 0)
              (setq isa-list (append isa-list (list isa))))))
    (while (progn
             (setq relationship-name (read-string "relationship type: "))
             (and
              (> (length relationship-name) 0)
              (progn
                (setq relationship-term (read-string "To id: "))
                (setq relationship-list
                      (append relationship-list
                              (list (list relationship-name relationship-term))))))))
    (insert (obo-new-term term-name namespace term-def isa-list relationship-list))))

(defun obo-add-typedef (id)
  "Adds a typedef"
  (interactive "sId: ")
  (insert (obo-new-typedef id)))

(defun obo-add-header (namespace)
  "Adds a term"
  (interactive "sNamespace: ")
  (setq obo-namespace namespace)
  (insert (obo-new-header namespace)))

(defun obo-add-instance (inst-name term)
  "Adds an instance"
  (interactive "sInstance Name: \nsTerm: ")
  (let (rel-type
        rel-inst
        rel-list)
    (setq rel-list '())
    (while (progn
             (setq rel-type (read-string "Relation type: "))
             (and
              (> (length rel-type) 0)
              (progn
                (setq rel-inst (read-string "To: "))
                (setq rel-list
                      (append rel-list
                              (list (list rel-type rel-inst))))))))
    (insert (obo-new-instance inst-name term rel-list))))



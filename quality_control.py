##############################################################################
#
# Copyright (c) 2010-2012 NaN Projectes de Programari Lliure, S.L.
#                         All Rights Reserved.
#                         http://www.NaN-tic.com
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from decimal import Decimal
import time

from osv import fields, osv
from tools.safe_eval import safe_eval
import decimal_precision as dp


class qc_proof_method(osv.osv):
    """
    This model stores a method for doing a test.
    Examples of methods are: "Eu.Pharm.v.v. (2.2.32)" or "HPLC"
    """
    _name = 'qc.proof.method'
    _description = 'Method'

    _columns = {
        'name': fields.char('Name', size=100, required=True, select=True,
                translate=True),
        'active': fields.boolean('Active', select=True),
        'company_id': fields.many2one('res.company', 'Company'),
    }

    _defaults = {
        'active': lambda *a: True,
        'company_id': lambda self, cr, uid, c:
                self.pool.get('res.company')._company_default_get(cr, uid,
                        'qc.proof.method', context=c),
    }
qc_proof_method()


class qc_posible_value(osv.osv):
    """
    This model stores all possible values of qualitative proof.
    """
    _name = 'qc.posible.value'

    _columns = {
        'name': fields.char('Name', size=200, required=True, select=True,
                translate=True),
        'active': fields.boolean('Active', select=True),
        'company_id': fields.many2one('res.company', 'Company'),
    }

    _defaults = {
        'active': lambda *a: True,
        'company_id': lambda self, cr, uid, c:
                self.pool.get('res.company')._company_default_get(cr, uid,
                        'qc.posible.value', context=c),
    }

    def search(self, cr, uid, args, offset=0, limit=None, order=None,
            context=None, count=False):
        if context is None:
            context = {}
        if context.get('proof_id'):
            ctx = context.copy()
            del ctx['proof_id']
            # TODO: check if its possible to do:  self.search(cr, uid, [
            #             ('proof_ids', 'in', [context['proof_id']]),
            #         ], context=ctx)
            proof = self.pool.get('qc.proof').browse(cr, uid,
                    context['proof_id'], ctx)
            result = [x.id for x in proof.value_ids]
            args = args[:]
            args.append(('id', 'in', result))
        return  super(qc_posible_value, self).search(cr, uid, args, offset,
                limit, order, context, count)
qc_posible_value()


class qc_proof(osv.osv):
    """
    This model stores proofs which will be part of a test. Proofs are
    classified between qualitative (such as color) and quantitative
    (such as density).

    Proof must be related with method, and Poof-Method relation must be unique

    A name_search on this model will search on 'name' field but also on any of
    its synonyms.
    """
    _name = 'qc.proof'

    # qc.proof
    def _synonyms(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for proof in self.browse(cr, uid, ids, context):
            texts = []
            for syn in proof.synonym_ids:
                texts.append(syn.name)
            result[proof.id] = ', '.join(texts)
        return result

    _columns = {
        'name': fields.char('Name', size=200, required=True, select=True,
                translate=True),
        'ref': fields.char('Code', size=30, select=True),
        'active': fields.boolean('Active', select=True),
        'synonym_ids': fields.one2many('qc.proof.synonym', 'proof_id',
                'Synonyms'),
        'type': fields.selection([
                    ('qualitative', 'Qualitative'),
                    ('quantitative', 'Quantitative'),
                ], 'Type', select=True, required=True),
        'value_ids': fields.many2many('qc.posible.value',
                'qc_proof_posible_value_rel', 'proof_id', 'posible_value_id',
                'Posible Values'),
        'synonyms': fields.function(_synonyms, method=True, type='char',
                size='1000', string='Synonyms', store=False),
        'company_id': fields.many2one('res.company', 'Company'),
    }

    _defaults = {
        'active': lambda *a: True,
        'company_id': lambda self, cr, uid, c:
                self.pool.get('res.company')._company_default_get(cr, uid,
                        'qc.proof', context=c),
    }

    # qc.proof
    def name_search(self, cr, uid, name='', args=None, operator='ilike',
            context=None, limit=None):
        result = super(qc_proof, self).name_search(cr, uid, name, args,
                operator, context, limit)
        if name:
            ids = [x[0] for x in result]
            new_ids = []
            syns = self.pool.get('qc.proof.synonym').name_search(cr, uid, name,
                    args, operator, context, limit)
            syns = [x[0] for x in syns]
            for syn in self.pool.get('qc.proof.synonym').browse(cr, uid, syns,
                    context):
                if not syn.proof_id.id in ids:
                    new_ids.append(syn.proof_id.id)
            result += self.name_get(cr, uid, new_ids, context)
        return result

    # qc.proof
    def name_get(self, cr, uid, ids, context=None):
        result = []
        for proof in self.browse(cr, uid, ids, context):
            text = proof.name
            if proof.synonyms:
                text += "  [%s]" % proof.synonyms
            result.append((proof.id, text))
        return result
qc_proof()


class qc_proof_synonym(osv.osv):
    """
    Proofs may have synonyms. These are used because suppliers may use
    different names for the same proof.
    """
    _name = 'qc.proof.synonym'

    _columns = {
        'name': fields.char('Name', size=200, required=True, select=True,
                translate=True),
        'proof_id': fields.many2one('qc.proof', 'Proof', required=True),
        'company_id': fields.many2one('res.company', 'Company'),
    }

    _defaults = {
        'company_id': lambda self, cr, uid, c:
                self.pool.get('res.company')._company_default_get(cr, uid,
                        'qc.proof.synonym', context=c),
        }
qc_proof_synonym()


def _links_get(self, cr, uid, context={}):
    """
    Returns a list of tuples of 'model names' and 'Model title' to use as
    typs in reference fields.
    """
    test_link_proxy = self.pool.get('qc.test.link')
    ids = test_link_proxy.search(cr, uid, [])
    res = test_link_proxy.read(cr, uid, ids, ['object', 'name'], context)
    return [(r['object'], r['name']) for r in res]


class qc_test_link(osv.osv):
    """
    This model is used to manage available models to link in the Reference
    fields of qc.test and qc.test.template
    """
    _name = 'qc.test.link'
    _description = "Test Reference Types"
    _order = 'priority'

    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'object': fields.char('Object', size=64, required=True),
        'priority': fields.integer('Priority'),
    }

    _defaults = {
        'priority': 5,
    }
qc_test_link()


class qc_test_template_category(osv.osv):
    """
    This model is used to categorize proof templates.
    """
    _name = 'qc.test.template.category'

    # qc.test.template.category
    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        reads = self.read(cr, uid, ids, [
                    'name',
                    'parent_id',
                ], context=context)
        res = []
        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1] + ' / ' + name
            res.append((record['id'], name))
        return res

    # qc.test.template.category
    def _complete_name(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    # qc.test.template.category
    def _check_recursion(self, cr, uid, ids):
        level = 100
        while len(ids):
            cr.execute("""SELECT DISTINCT parent_id
                    FROM qc_test_template_category
                    WHERE id IN (%s)""" % ",".join(map(str, ids)))
            ids = [x[0] for x in cr.fetchall() if x[0] != None]
            if not level:
                return False
            level -= 1
        return True

    _columns = {
        'name': fields.char('Category Name', required=True, size=64,
                translate=True),
        'parent_id': fields.many2one('qc.test.template.category',
                'Parent Category', select=True),
        'complete_name': fields.function(_complete_name, method=True,
                type='char', string='Full Name'),
        'child_ids': fields.one2many('qc.test.template.category', 'parent_id',
                'Child Categories'),
        'active': fields.boolean('Active', help="The active field allows you "
                "to hide the category without removing it."),
        'company_id': fields.many2one('res.company', 'Company'),
    }

    _constraints = [
        (_check_recursion, 'Error ! You can not create recursive categories.',
                ['parent_id'])
    ]

    _defaults = {
        'active': lambda *a: True,
        'company_id': lambda self, cr, uid, c:
                self.pool.get('res.company')._company_default_get(cr, uid,
                        'qc.test.template.category', context=c),
    }
qc_test_template_category()


class qc_test_template(osv.osv):
    """
    A template is a group of proofs to with the values that make them valid.
    """
    _name = 'qc.test.template'
    _description = 'Test Template'

    # qc.test.template
    def _default_name(self, cr, uid, context=None):
        if context and context.get('reference_model', False):
            ref_id = context.get('reference_id')
            if not ref_id:
                ref_id = context.get('active_id')
            if ref_id:
                source = self.pool.get(context['reference_model']).browse(cr,
                        uid, ref_id, context)
                if hasattr(source, 'name'):
                    return source.name

    # qc.test.template
    def _default_object_id(self, cr, uid, context=None):
        if context and context.get('reference_model', False):
            return '%s,%d' % (context['reference_model'],
                    context['reference_id'])
        else:
            return False

    # qc.test.template
    def _default_type(self, cr, uid, context=None):
        if context and context.get('reference_model'):
            return 'related'
        else:
            return False

    _columns = {
        'active': fields.boolean('Active', select=True),
        'name': fields.char('Name', size=200, required=True, translate=True,
                select=True),
        'test_template_line_ids': fields.one2many('qc.test.template.line',
                'test_template_id', 'Lines'),
        'object_id': fields.reference('Reference Object', selection=_links_get,
                size=128),
        'fill_correct_values': fields.boolean('Fill With Correct Values'),
        'type': fields.selection([
                    ('generic', 'Generic'),
                    ('related', 'Related'),
                ], 'Type', select=True),
        'category_id': fields.many2one('qc.test.template.category',
                'Category'),
        'formula': fields.text('Formula'),
        'company_id': fields.many2one('res.company', 'Company'),
        'uom_id': fields.many2one('product.uom', 'UoM'),
    }

    _defaults = {
        'name': _default_name,
        'active': lambda *a: True,
        'object_id': _default_object_id,
        'type': _default_type,
        'company_id': lambda self, cr, uid, c:
                self.pool.get('res.company')._company_default_get(cr, uid,
                        'qc.test.template', context=c),
    }
qc_test_template()


class qc_test_template_line(osv.osv):
    _name = 'qc.test.template.line'
    _order = 'sequence asc'

    def onchange_proof_id(self, cr, uid, ids, proof_id, context):
        if not proof_id:
            return {}

        proof = self.pool.get('qc.proof').browse(cr, uid, proof_id, context)
        return {
            'value': {
                'type': proof.type,
            }}

    _columns = {
        'name': fields.char('Name', size=64),
        'sequence': fields.integer('Sequence', required=True),
        'test_template_id': fields.many2one('qc.test.template',
                'Test Template', select=True),
        'proof_id': fields.many2one('qc.proof', 'Proof', required=True,
                select=True),
        'valid_value_ids': fields.many2many('qc.posible.value',
                'qc_template_value_rel', 'template_line_id', 'value_id',
                'Values'),
        'method_id': fields.many2one('qc.proof.method', 'Method', select=True),
        'notes': fields.text('Notes'),
        # Only if quantitative
        'min_value': fields.float('Min',
                digits_compute=dp.get_precision('Quality Control')),
        # Only if quantitative
        'max_value': fields.float('Max',
                digits_compute=dp.get_precision('Quality Control')),
        # Only if quantitative
        'uom_id': fields.many2one('product.uom', 'UoM'),
        'type': fields.selection([
                    ('qualitative', 'Qualitative'),
                    ('quantitative', 'Quantitative'),
                ], 'Type', select=True),
        'company_id': fields.related('test_template_id', 'company_id',
                type='many2one', relation='res.company', string='Company',
                store=True, readonly=True),
    }

    _defaults = {
        'sequence': lambda *b: 1,
    }
qc_test_template_line()


class qc_test(osv.osv):
    """
    This model contains an instance of a test template.
    """
    _name = 'qc.test'

    # qc.test
    def _success(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for test in self.browse(cr, uid, ids, context):
            success = True
            proof = {}
            for line in test.test_line_ids:
                # Check the partner (test method). Check that at least the test
                #     is a test method with some success.
                proof[line.proof_id.id] = (proof.get(line.proof_id.id, False)
                        or line.success)

            for p in proof:
                if not proof[p]:
                    success = False
                    break

            result[test.id] = success
        return result

    # qc.test
    def _default_object_id(self, cr, uid, context=None):
        if context and context.get('reference_model', False):
            return '%s,%d' % (
                    context['reference_model'],
                    context['reference_id'])
        else:
            return False

    # qc.test
    def _action_calc_formula(self, cr, uid, ids, field_names, args, context):
        result = {}.fromkeys(ids, 0)
        for test in self.browse(cr, uid, ids, context):
            vals = {}
            for line in test.test_line_ids:
                if line.name and line.proof_type == 'quantitative':
                    vals[line.name] = line.actual_value_qt

            if not  test.formula:
                result[test.id] = 0
                continue

            try:
                value = safe_eval(test.formula, vals)
                result[test.id] = value
            except NameError:
                pass
                #raise osv.except_osv( _('Error:'), msg )
        return result

    _columns = {
        'name': fields.char('Number', size=64, required=True, select=True),
        'date': fields.datetime('Date', required=True, readonly=True,
                select=True, states={
                    'draft': [('readonly', False)],
                }),
        'object_id': fields.reference('Reference', selection=_links_get,
                size=128, readonly=True, select=True, states={
                    'draft': [('readonly', False)],
                }),
        'test_template_id': fields.many2one('qc.test.template', 'Test template',
                select=True, states={
                    'success': [('readonly', True)],
                    'failed': [('readonly', True)],
                }),
        'test_line_ids': fields.one2many('qc.test.line', 'test_id',
                'Test Lines', states={
                    'success': [('readonly', True)],
                    'failed': [('readonly', True)],
                }),
        'test_internal_note': fields.text('Internal Note', states={
                    'success': [('readonly', True)],
                    'failed': [('readonly', True)],
                }),
        'test_external_note': fields.text('External Note', states={
                    'success': [('readonly', True)],
                    'failed': [('readonly', True)],
                }),
        'state': fields.selection([
                ('draft', 'Draft'),
                ('waiting', 'Waiting Supervisor Approval'),
                ('success', 'Quality Success'),
                ('failed', 'Quality Failed'),
            ], 'State', readonly=True, select=True),
        'success': fields.function(_success, method=True, type='boolean',
                string='Success', select=True, store=True,
                help='This field will be active if all tests have succeeded.'),
        'formula': fields.text('Formula', readonly=1),
        'formula_result': fields.function(_action_calc_formula, method=True,
                string='Formula Value', type='float',
                digits_compute=dp.get_precision('Quality Control')),
        'uom_id': fields.many2one('product.uom', 'UoM'),
        'company_id': fields.many2one('res.company', 'Company'),
    }

    _defaults = {
        'name': lambda obj, cr, uid, context: \
                obj.pool.get('ir.sequence').get(cr, uid, 'qc.test'),
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'state': 'draft',
        'success': False,
        'object_id': _default_object_id,
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')\
                ._company_default_get(cr, uid, 'qc.test', context=c),
    }

    # qc.test
    def _calc_line_vals_from_template(self, cr, uid, test_id, template_line,
            fill_correct_values, context):
        data = {
            'name': template_line.name,
            'test_id': test_id,
            'method_id': template_line.method_id.id,
            'proof_id': template_line.proof_id.id,
            'test_template_line_id': template_line.id,
            'notes': template_line.notes,
            'min_value': template_line.min_value,
            'max_value': template_line.max_value,
            'uom_id': template_line.uom_id.id,
            'test_uom_id': template_line.uom_id.id,
            'proof_type': template_line.proof_id.type,
        }
        if fill_correct_values:
            if template_line.type == 'qualitative':
                # Fill with the first correct value found.
                data['actual_value_ql'] = (len(template_line.valid_value_ids)
                        and template_line.valid_value_ids[0]
                        and template_line.valid_value_ids[0].id
                        or False)
            else:
                # Fill with value in the range.
                data['actual_value_qt'] = template_line.min_value
                data['test_uom_id'] = template_line.uom_id.id
        return data

    # qc.test
    def set_test_template(self, cr, uid, ids, template_id, force_fill=False,
                context=None):
        test_line_proxy = self.pool.get('qc.test.line')

        if context is None:
            context = {}
        template = self.pool.get('qc.test.template').browse(cr, uid,
                template_id, context=context)
        for test_id in ids:
            self.write(cr, uid, test_id, {
                        'test_template_id': template_id,
                        'formula': template.formula,
                        'uom_id': template.uom_id and template.uom_id.id
                    }, context)

            test = self.browse(cr, uid, test_id, context)

            if len(test.test_line_ids) > 0:
                test_line_proxy.unlink(cr, uid,
                        [x.id for x in test.test_line_ids], context)

            fill = test.test_template_id.fill_correct_values or False
            for line in test.test_template_id.test_template_line_ids:
                data = self._calc_line_vals_from_template(cr, uid, test_id,
                        line, fill or force_fill, context)

                test_line_id = test_line_proxy.create(cr, uid,
                        data, context)
                test_line_proxy.write(cr, uid, [test_line_id], {
                            'valid_value_ids': [
                                (6, 0, [x.id for x in line.valid_value_ids]),
                            ],
                        }, context)
            # It writes again the test to force to recalculate 'success' field
            self.write(cr, uid, test_id, {
                        'formula': template.formula,
                        'uom_id': template.uom_id and template.uom_id.id
                    }, context)
        return True

    # qc.test
    def test_state(self, cr, uid, ids, mode, context):
        '''
        Currently not used.
        Probably it will be completed (this code is a fake) when the
        nan_stock_production_lot_quality_control module will be implemented
        '''
        quality_check = False

        if mode == 'failed':
            return not quality_check
        if mode == 'success':
            return quality_check
        return False

    # qc.test
    def action_workflow_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
                    'state': 'draft'
                }, context)
        return True

    # qc.test
    def action_workflow_waiting(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
                    'state': 'waiting'
                }, context)
        return True

    # qc.test
    def action_workflow_success(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
                    'state': 'success'
                }, context)
        return True

    # qc.test
    def action_workflow_failed(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
                    'state': 'failed'
                }, context)
        return True

    # qc.test
    def test_workflow_draft(self, cr, uid, ids, context=None):
        # if qc_test.state=='success':
        return True

    # qc.test
    def copy(self, cr, uid, test_id, default=None, context=None):
        if context is None:
            context = {}

        if default is  None:
            default = {}

        if not 'name' in default:
            default['name'] = self.pool.get('ir.sequence').get(cr, uid,
                    'qc.test')
        if not 'date' in default:
            default['date'] = time.strftime('%Y-%m-%d %H:%M:%S')

        return super(qc_test, self).copy(cr, uid, test_id, default, context)

    # qc.test
    def create(self, cr, uid, datas, context=None):
        if context and context.get('reference_model'):
            datas['object_id'] = context['reference_model'] + "," + \
                    str(context['reference_id'])
        return super(qc_test, self).create(cr, uid, datas, context=context)
qc_test()


class qc_test_line(osv.osv):
    _name = 'qc.test.line'
    _rec_name = 'proof_id'

    # qc.test.line
    def quality_test_check(self, cr, uid, ids, field_name, field_value,
            context):
        res = {}
        lines = self.browse(cr, uid, ids, context)
        for line in lines:
            if line.proof_type == 'qualitative':
                res[line.id] = self.quality_test_qualitative_check(cr, uid,
                        line, context)
            else:
                res[line.id] = self.quality_test_quantitative_check(cr, uid,
                        line, context)
        return res

    # qc.test.line
    def quality_test_qualitative_check(self, cr, uid, test_line, context):
        if test_line.actual_value_ql in test_line.valid_value_ids:
            return True
        else:
            return False

    # qc.test.line
    def quality_test_quantitative_check(self, cr, uid, test_line, context):
        amount = self.pool.get('product.uom')._compute_qty(cr, uid,
                test_line.uom_id.id, test_line.actual_value_qt,
                test_line.test_uom_id.id)

        try:
            damount = Decimal(str(amount))
            min_amount = Decimal(str(test_line.min_value))
            max_amount = Decimal(str(test_line.max_value))
        except NameError:
            return False

        if damount >= min_amount and damount <= max_amount:
            return True
        else:
            return False

    _columns = {
        'name': fields.char('Name', size=64),
        'test_id': fields.many2one('qc.test', 'Test'),
        'test_template_line_id': fields.many2one('qc.test.template.line',
                'Test Template Line', readonly=True),
        'proof_id': fields.many2one('qc.proof', 'Proof', readonly=True),
        'method_id': fields.many2one('qc.proof.method', 'Method',
                readonly=True),
        'valid_value_ids': fields.many2many('qc.posible.value',
                'qc_test_value_rel', 'test_line_id', 'value_id', 'Values'),
        'actual_value_qt': fields.float('Qt.Value',
                digits_compute=dp.get_precision('Quality Control'),
                help="Value of the result if it is a quantitative proof."),
        'actual_value_ql': fields.many2one('qc.posible.value', 'Ql.Value',
                help="Value of the result if it is a qualitative proof."),
        'notes': fields.text('Notes', readonly=True),
        'min_value': fields.float('Min', readonly=True,
                digits_compute=dp.get_precision('Quality Control'),
                help="Minimum valid value if it is a quantitative proof."),
        'max_value': fields.float('Max', readonly=True,
                digits_compute=dp.get_precision('Quality Control'),
                help="Maximum valid value if it is a quantitative proof."),
        'uom_id': fields.many2one('product.uom', 'UoM', readonly=True,
                help="UoM for minimum and maximum values if it is a "
                "quantitative proof."),
        'test_uom_id': fields.many2one('product.uom', 'Uom Test', help="UoM "
                "of the value of the result if it is a quantitative proof."),
        'proof_type': fields.selection([
                    ('qualitative', 'Qualitative'),
                    ('quantitative', 'Quantitative'),
                ], 'Proof Type', readonly=True),
        'success': fields.function(quality_test_check, type='boolean',
                method=True, string="Success?", select=True),
        'company_id': fields.related('test_id', 'company_id', type='many2one',
                relation='res.company', string='Company', store=True,
                readonly=True),
    }
qc_test_line()


class qc_test_wizard(osv.osv_memory):
    """This wizard is responsible for setting the proof template for a given
    test. This will not only fill in the 'test_template_id' field, but will
    also fill in all lines of the test with the corresponding lines of the
    template."""
    _name = 'qc.test.set.template.wizard'

    # qc.test.set.template.wizard
    def _default_test_template_id(self, cr, uid, context):
        test_id = context.get('active_id')
        test = self.pool.get('qc.test').browse(cr, uid, test_id, context)
        ids = self.pool.get('qc.test.template').search(cr, uid, [
                    ('object_id', '=', test.object_id),
                ], context=context)
        return ids and ids[0] or False

    _columns = {
        'test_template_id': fields.many2one('qc.test.template', 'Template'),
    }

    _defaults = {
        'test_template_id': _default_test_template_id,
    }

    # qc.test.set.template.wizard
    def action_create_test(self, cr, uid, ids, context):
        wizard = self.browse(cr, uid, ids[0], context)
        self.pool.get('qc.test').set_test_template(cr, uid,
                [context['active_id']], wizard.test_template_id.id,
                context=context)
        return {
            'type': 'ir.actions.act_window_close',
        }

    # qc.test.set.template.wizard
    def action_cancel(self, cr, uid, ids, context=None):
        return {
            'type': 'ir.actions.act_window_close',
        }
qc_test_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

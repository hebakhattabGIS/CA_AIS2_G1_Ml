
# Definition for singly-linked list.
class ListNode:
     def __init__(self, val=0, next=None):
         self.val = val
         self.next = next

class Solution:
    def addTwoNumbers(self, l1: ListNode, l2: ListNode) -> ListNode:
        """
        :type l1: Optional[ListNode]
        :type l2: Optional[ListNode]
        :rtype: Optional[ListNode]
        """
        result = ListNode()  #placeholder 
        current = result
        carry = 0
        while l1 or l2 or carry:
            # Get values or 0 if the list ended
            v1 = l1.val if l1 else 0
            v2 = l2.val if l2 else 0

            # Add digits + carry
            total = v1 +v2 + carry
            carry = total // 10
            digit = total % 10

            #create new node
            current.next = ListNode(digit)
            current = current.next

            #move forward
            if l1: l1 = l1.next
            if l2: l2 = l2.next

        return result.next


# Build example lists: [2,4,3] and [5,6,4]
l1 = ListNode(2, ListNode(4, ListNode(3)))
l2 = ListNode(5, ListNode(6, ListNode(4)))
x = ListNode()
result = Solution()
x = result.addTwoNumbers(l1, l2)

# Print result
while x:
    print(x.val, end=" ")
    x = x.next
